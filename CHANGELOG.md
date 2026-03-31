# CHANGELOG

こちらの CHANGELOG は Keep a Changelog の形式に準拠しています。  
リリースノートはコードベース（src/kabusys 以下）から実装内容を推測して作成しています。

全般的な方針
- DuckDB をメインのローカル分析ストアとして利用する設計。
- ETL / データ処理・研究・AI スコアリング・カレンダー管理などをモジュール化。
- ルックアヘッドバイアス回避のため、内部実装で datetime.today()/date.today() を不必要に参照しない方針を徹底。
- 外部 API 呼び出しは冪等性・フェイルセーフ・エクスポネンシャルバックオフを重視した実装。

なお、必要な環境変数（欠けていると ValueError を送出するもの）:
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- OpenAI API を利用する機能は OPENAI_API_KEY が必要（関数引数で注入可能）

-----------------------------------------------------------------

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ基盤
  - 基本パッケージ定義を追加（kabusys/__init__.py、バージョン 0.1.0）。
  - モジュール群を公開: data, research, ai, monitoring 等を想定した構成。

- 環境設定・自動ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込みする機能を実装。
  - OS 環境変数を保護するための protected 機能と、.env.local による上書きサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサ実装:
    - export KEY=value 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープサポート。
    - インラインコメントの取り扱いや無効行の無視。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabu ステーション / Slack / DB パス（DuckDB/SQLite）/監視閾値 / 環境（development/paper_trading/live）/ログレベル等。
    - 必須設定キーは未設定時に ValueError を送出。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別のスコアを生成。
    - JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して DB クエリに使用する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり記事数と文字数上限のトリム処理を実装。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）、およびレスポンスの堅牢なバリデーション。
    - レスポンスは JSON モードを想定しつつ、前後に余計なテキストが混ざる場合の復元処理も実装。
    - スコアは ±1.0 にクリップ。ai_scores テーブルへは部分成功を考慮した DELETE→INSERT の冪等書き込みを実行。
    - テスト容易性のため _call_openai_api を patch で差し替えられる設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードに基づく raw_news タイトル抽出、OpenAI 呼び出し、リトライ、JSON パースの堅牢化を実装。
    - API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - 設定可能な閾値・重み・モデル（デフォルト gpt-4o-mini）等を定数化。

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR/相対 ATR）、Value（PER/ROE）等を DuckDB の SQL/ウィンドウ関数で計算する関数群を実装。
    - 入力は prices_daily / raw_financials テーブル。データ不足時の None 帰却、結果は (date, code) ベースの dict リストとして返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応し、ホライズン検証（正の整数かつ <=252）を行う。
    - IC（Information Coefficient）計算（calc_ic）: コードで結合してスピアマンのランク相関を算出。使用データが少ない場合は None。
    - ランク関数（rank）: 同順位は平均ランク、浮動小数丸めを利用して ties の誤差を低減。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。

- データ（Data）モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定・次/前営業日取得・期間内営業日列挙・SQ 判定ロジックを実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得 → 保存（冪等）を行う。バックフィルや健全性チェックを実装。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを追加（ETL 実行結果の構造化）。
    - ETL の差分取得・保存・品質チェックの設計に沿ったユーティリティを実装（jquants_client と quality モジュールに依存）。
    - DuckDB に対するテーブル存在チェックや最大日付取得等のユーティリティを実装。
    - executemany の空リスト禁止（DuckDB 0.10）に配慮した保護コードを導入。

- その他
  - モジュール間結合を避ける設計（例: regime_detector と news_nlp で OpenAI 呼び出しラッパーを共有しない）。
  - 多くの箇所で明示的なログ出力（info/debug/warning/exception）を追加し、運用時の可観測性を高める。

### 変更 (Changed)
- 初回公開のため該当なし（初版）。

### 修正 (Fixed)
- 初回公開のため該当なし（初版）。

### 非推奨 (Deprecated)
- 初回公開のため該当なし（初版）。

### 削除 (Removed)
- 初回公開のため該当なし（初版）。

### セキュリティ (Security)
- OpenAI や外部 API キーの取得は明示的に引数注入可能。環境変数依存部分は ValueError で明確に失敗させる方針（運用ミスを早期発見可能）。

-----------------------------------------------------------------

注意事項（運用上のポイント）
- OpenAI 呼び出しは外部料金・レート制限が発生するため、ローカルテスト時は _call_openai_api をモックすることを推奨します。
- .env 自動ロードはプロジェクトルートの検出に依存するので、パッケージ配布後/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと環境干渉を避けられます。
- DuckDB schema（prices_daily, raw_news, market_calendar, ai_scores, market_regime, raw_financials 等）は本リリースの機能前提となるため、初期化スクリプトやマイグレーションの整備が必要です。

-----------------------------------------------------------------

今後の想定改善ポイント（将来のリリース候補）
- ai モジュールのモデル選択を設定から切り替え可能にする（柔軟なモデル管理）。
- jquants_client と quality モジュールの具象実装を含めた ETL のデフォルトワークフロー提供。
- より詳細なユニット/統合テスト、空・異常応答に対するカバレッジ強化。
- ロギングの標準化（構造化ログ/メトリクス出力等）。

---  
以上。必要に応じて日付・バージョンや項目の粒度を調整した版を作成します。