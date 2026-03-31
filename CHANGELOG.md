# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
履歴は逆順（新しいリリースを上）で記載します。

## [0.1.0] - 初回リリース (未公開日付)
初期実装リリース。日本株自動売買システムのコアライブラリを提供します。主要コンポーネントはデータETL、マーケットカレンダー管理、ファクター計算・解析、ニュースNLP・レジーム判定、設定管理などです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報の公開（kabusys.__version__ = "0.1.0"）および主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml で探索。
    - 読み込み順: OS 環境 > .env.local (override) > .env。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト用）。
  - .env パーサの堅牢化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント判定の改善）。
  - Settings クラスを実装して、必須/任意の設定値をプロパティ経由で取得。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi), SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
    - データベースパス設定: DUCKDB_PATH / SQLITE_PATH（デフォルトパスを設定）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジック。
- AI モジュール (kabusys.ai)
  - ニュースNLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を計算、ai_scores テーブルへ書き込む機能（score_news）。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）。
    - バッチサイズ、記事・文字数トリム、JSON Mode の利用、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - テスト容易性のため API 呼び出し関数を patch 可能に設計（_call_openai_api を差し替え可能）。
    - DuckDB の executemany に関する注意（空リスト渡し回避）に対応した冪等書き込み（DELETE → INSERT）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存（score_regime）。
    - prices_daily / raw_news を利用したデータ取得、OpenAI 呼び出しのリトライ・フォールバック（API失敗時は macro_sentiment=0.0）。
    - レジームスコアの閾値、スケーリング等の定数を定義。
- データモジュール (kabusys.data)
  - 市場カレンダー管理 (calendar_management)
    - market_calendar テーブル保持・夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB未取得日には曜日ベースのフォールバック（週末除外）を一貫して使用する設計。
    - 最大探索日数制限やバックフィル、健全性チェックを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー概要を保持）。
    - 差分取得・バックフィル・品質チェックの方針を実装（実際の jquants_client / quality モジュールと連携する設計）。
    - 内部ヘルパー: テーブル存在チェック・最大日付取得など。
- リサーチモジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離 (calc_momentum)。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率 (calc_volatility)。
    - バリュー: PER, ROE（raw_financials から最新の財務データを取得）(calc_value)。
    - DuckDB 上で SQL と Python を組み合わせた実装、データ不足時の None 処理。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 (calc_forward_returns)：複数ホライズンに対応、引数検証。
    - IC 計算 (calc_ic)：Spearman（ランク相関）に基づく Information Coefficient 計算（同順位の平均ランク処理含む）。
    - ランク変換ユーティリティ (rank)。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を計算。
- 公開 API のエクスポート
  - data.etl: ETLResult を再エクスポート。

### 変更 (Changed)
- 初期リリースのため該当なし（新規実装）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 廃止 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- 初期リリース。OpenAI API キー等の機密情報は環境変数で管理する設計（必須項目は Settings のプロパティで検証）。

## 注意事項 / 実装上の設計・制約
- OpenAI 関連
  - gpt-4o-mini と JSON Mode を使用する前提で実装（OpenAI SDK のバージョン依存性あり）。
  - APIキーが未設定の場合、score_news / score_regime は ValueError を送出する。
  - レスポンスの堅牢化（JSON 前後の余計なテキストの抽出等）を行っているが、LLM 出力の保証はできないためバリデーション失敗時は該当チャンクをスキップする実装。
- DuckDB 関連
  - executemany に空リストを渡すと失敗するバージョンを考慮して空チェックを行っている。
  - 日付取り扱いはすべて date オブジェクト（タイムゾーン混入を避ける）。
- ルックアヘッドバイアス対策
  - 各種処理は内部で datetime.today() / date.today() を直接参照しないよう設計（target_date を引数で与える設計）。
  - prices_daily などのクエリでは target_date 未満/未満等の排他条件を用いてルックアヘッドを避ける。
- フェイルセーフ
  - API 呼び出し失敗時は即例外を投げるのではなく、フォールバック値（例: macro_sentiment = 0.0）や該当チャンクのスキップで継続する設計。
- 未実装・制限
  - calc_value では PBR・配当利回りは未実装。
  - news_nlp のスコアは現フェーズでは sentiment_score と ai_score を同値で保存している。
- テスト向けフック
  - OpenAI 呼び出し部分は内部関数を patch することでテスト時に差し替え可能。

---

将来のリリースでは以下を予定／検討:
- strategy / execution / monitoring の具体的実装（発注ロジック・実行系・監視基盤）。
- OpenAI モデルの選択肢・プロンプト改善、ロギング・監査出力の強化。
- ETL の実行スケジューラ、より詳細な品質チェックスコアリングと自動アラート連携。

--- 

（注）本 CHANGELOG は配布されたソースコードからの推測に基づいて記載しています。リポジトリの実際のコミット履歴やリリース日付は別途管理してください。