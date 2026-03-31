# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリースポリシー: セマンティックバージョニングを想定します（現状のパッケージバージョン: 0.1.0）。
- 日付はリリース日を記載しています（この CHANGELOG はコードベースの内容から推測して作成しています）。

## [Unreleased]

- なし（初回リリース相当の状態からの記録のため、未リリース変更はありません）。
- 今後の改善候補（実装上のメモ、将来的な追加予定）
  - strategy / execution / monitoring モジュールの公開 API 実装・文書化
  - 単体テスト・統合テストの追加（OpenAI / J-Quants 呼び出しのモック化）
  - 性能・並列化の改善（大規模ニュースバッチ処理時の最適化）
  - エラー監視・メトリクス収集の強化（Prometheus / Sentry 等）

---

## [0.1.0] - 2026-03-31

初回公開リリース（コードベースから推測）。日本株自動売買プラットフォームの基盤機能群を実装。

### Added
- パッケージ基盤
  - パッケージメタデータ: kabusys.__version__ = "0.1.0" を設定。
  - パッケージ公開 API: __all__ で "data", "strategy", "execution", "monitoring" を想定してエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - .env パースの堅牢化:
    - コメント行や export プレフィックスに対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの扱い（クォートなしの '#' は直前が空白/タブのときにコメントと扱う等）。
  - Settings クラス:
    - J-Quants, kabu API, Slack, DB パス、環境種別・ログレベル等の取得プロパティを提供。
    - 必須環境変数未設定時に ValueError を送出する _require 実装。
    - env / log_level の妥当性チェック（許容値の列挙）。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）を JSON Mode でバッチ呼び出しし、各銘柄のセンチメント（-1.0〜1.0）を ai_scores テーブルへ保存。
    - バッチ処理（_BATCH_SIZE=20）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / サーバー 5xx に対する指数バックオフ・リトライ実装。
    - レスポンス検証ロジック（JSON 抽出、results リスト、各要素の code/score 検証、スコアのクリップ）。
    - データベース書き込みは部分失敗耐性を考慮し、処理済みコードのみ DELETE→INSERT（冪等性確保）。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、target_date ベースでウィンドウを算出（calc_news_window 実装）。
    - API 呼び出し箇所はテスト容易性のため _call_openai_api を介して差し替え可能。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を算出。
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラーやパース失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI 呼出しのリトライ制御（5xx とネットワーク系に対して指数バックオフ）。
    - ルックアヘッド防止のため target_date 未満のデータのみ参照。

- 研究用・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（prices_daily 参照）。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の報告日を取得）。
    - SQL ベース実装で DuckDB を利用、データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一クエリで取得可能に実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（コード結合・None 除外・最小サンプル数制約）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ。
  - zscore_normalize は kabusys.data.stats から再エクスポート（research.__init__）。

- データ基盤 (kabusys.data)
  - calendar_management:
    - market_calendar テーブルをベースに営業時間判定・次/前営業日取得・期間内営業日取得・SQ 日判定を提供。
    - database が未取得の場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存、バックフィル・健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult dataclass を導入（取得数・保存数・品質問題・エラー等を格納、to_dict により品質問題をシリアライズ可能）。
    - 差分更新、バックフィル、品質チェック連携を想定した構成。
  - etl.py で ETLResult を再エクスポート。

- DuckDB と互換性を考慮した実装
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 の制約への対応）。
  - 日付値の DuckDB->date 変換ユーティリティを提供。

- ロギングと運用上の配慮
  - 各処理で情報・警告・例外ログを詳細に出力（例: データ不足、API リトライ、ROLLBACK の失敗等）。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を使った冪等処理や ROLLBACK 保護を実装。

### Changed
- （初回公開に相当するため、既存 API の互換性破壊はなし。実装上の設計方針を明確化）
  - ルックアヘッドバイアス対策を徹底（target_date ベースの設計に統一）。
  - OpenAI 呼び出しの扱いをニュース系とレジーム系で独立した内部呼出し関数に分離（モジュール結合の低減、テスト容易性向上）。

### Fixed
- .env パーサーの堅牢化により、以下の取りこぼしを修正（推定）
  - export プレフィックス付き行の不正処理
  - クォート内でのバックスラッシュエスケープ処理の誤動作
  - インラインコメントの誤判定

### Security
- 環境変数に依存する設計（必須トークンは Settings 経由で明示）
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API キーは score_news / score_regime の引数に注入可能か、環境変数 OPENAI_API_KEY を参照
- .env ファイル読み込み時に OS 環境変数を保護する protected キーセットを用いることで、意図しない上書きを防止。

### Known issues / Limitations
- OpenAI / J-Quants の外部 API 呼び出しに依存するため、実行環境ではそれらの認証情報が必要。
- strategy / execution / monitoring の具体的な発注ロジックはこのスナップショットでは未確認（パッケージ公開名に含まれるが実装ファイルの提示はなし）。
- DuckDB バージョン差異による SQL バインドの挙動に注意（コード中に回避策を実装済みだが、環境によって動作確認が必要）。
- 単体テスト・統合テストの存在についての情報はコードからは確認できない（テスト用フックは一部提供）。

---

（注）本 CHANGELOG は提供されたソースコードの内容・コメント・設計文書的記述から推測して作成しています。実際のコミット履歴やリリースノートに基づくものではないため、細部は実際の履歴と差異がある可能性があります。必要であれば、リポジトリのコミットログに基づくより厳密な CHANGELOG を生成します。