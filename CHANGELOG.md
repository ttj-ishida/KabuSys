# Keep a Changelog
すべての可視的な変更を日付順に記載します。セマンティックバージョニングに準拠しています。

フォーマットについては https://keepachangelog.com/ja/ を参照してください。

## [Unreleased]

- ドキュメント的な補足、内部リファクタリングや小さな改善を予定。

---

## [0.1.0] - 2026-03-31

初回公開リリース。以降の説明はコードベースから推測した主要な追加機能・設計方針・既知の制限事項をまとめたものです。

### 追加 (Added)

- パッケージ基盤
  - パッケージメタ情報と公開 API を定義（kabusys.__init__、バージョン "0.1.0"）。
  - モジュール群: data, research, ai, execution（プレースホルダ）, monitoring（プレースホルダ）, strategy（プレースホルダ）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env/.env.local の優先順位処理と OS 環境変数保護（.env.local は上書き可、既存 OS 変数は protected）。
  - 行パーサ実装: export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス公開: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、監視しきい値、KABUSYS_ENV、LOG_LEVEL などを環境変数から取得し検証するユーティリティ。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）に JSON mode で送信してセンチメントを得る。
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数上限（記事数: 10、文字数: 3000）によるトリム。
    - 再試行（429、ネットワーク、タイムアウト、5xx）に対する指数バックオフ。
    - レスポンス検証（JSON 抽出、results 配列、code と score の検証、スコアを ±1.0 にクリップ）。
    - 成果物は ai_scores テーブルへ安全に置換（該当 code のみ DELETE → INSERT、部分失敗に対する保護）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ニュースは news_nlp の calc_news_window を利用して収集し、最大 20 件を LLM に投げる。
    - OpenAI 呼び出しは独立実装、失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - 計算結果は冪等的に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。

  - AI クライアント呼び出し部はテスト容易性のため差し替え可能（_call_openai_api をモック可能）。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (data.calendar_management)
    - market_calendar テーブルを参照した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した方針。
    - 夜間バッチジョブ calendar_update_job により J-Quants API から差分取得・保存（バックフィル・健全性チェックあり）。

  - ETL 基盤 (data.pipeline / data.etl)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧などを集約）。
    - 差分更新、backfill、品質チェック（quality モジュール）を想定した設計（実装は pipeline に記載）。
    - jquants_client を用いた idempotent 保存を想定。

- Research（ファクター計算） (kabusys.research)
  - ファクター計算の実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取り出して PER / ROE を計算（EPS=0 や欠損は None）。PBR・配当利回りは未実装（注記あり）。
  - 特徴量探索:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: Spearman ランク相関（IC）を計算（必要レコード数が不足する場合は None）。
    - rank: 同順位は平均ランクへマッピング（round による丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計集約。

- 技術的設計の共通点（全体）
  - DuckDB を主要な分析データベースとして利用。
  - ルックアヘッドバイアスに注意して、関数内部で datetime.today()/date.today() を直接参照しない（target_date ベースで動作）。
  - 外部依存（pandas など）に頼らない実装方針（標準ライブラリ＋duckdb）。
  - OpenAI API は gpt-4o-mini を想定し、JSON mode を利用するプロンプト構成。

### 変更 (Changed)

- 初期リリースにつき変更履歴なし（初回導入機能の一覧を上記に記載）。

### 修正 (Fixed)

- 初期リリースにつき過去修正なし。ただし既知の実装上の問題点は下記参照。

### 既知の問題 (Known issues / Notes)

- data.pipeline._get_max_date の末尾に不完全な実装（タイポ）が存在:
  - ファイル末尾に "return date.fro" のような不完全な行があり、このままでは NameError / SyntaxError を引き起こす可能性があります。リリース直後は修正が必要です。
- calc_value:
  - PBR・配当利回りは現バージョンでは未実装。将来の拡張対象。
- AI モジュール:
  - OpenAI API キー未設定時は関数が ValueError を送出する（明示的な挙動）。運用時は OPENAI_API_KEY の設定が必須。
  - LLM レスポンスの不確実性に備え、API エラーやパース失敗時はフェイルセーフとしてスコア 0.0（レジーム判定）や対象外スキップ（ニューススコア）にフォールバックする設計。ただし部分的な欠落が発生すると書き込み件数が減る可能性がある。

### 必須環境変数（運用上の注意）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（AI 機能を利用する場合、引数で上書き可能）
- DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
- KABUSYS_ENV（development|paper_trading|live、デフォルト development）
- LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env 自動ロードを無効化可能

### マイグレーションノート / 運用メモ

- 初回セットアップ時は DuckDB スキーマ（prices_daily / raw_news / news_symbols / ai_scores / raw_financials / market_calendar / market_regime 等）を作成する必要がある（スキーマ定義は別途管理）。
- ETL 実行時は ETLResult で品質問題やエラーを集約・監査ログに保存することを推奨。
- OpenAI 呼び出しはテスト容易性のため _call_openai_api をモック可能。CI では環境変数なしでモックを行う運用が想定される。

---

今後の予定（想定）
- 上記の既知のバグ修正（pipeline のタイポ修正など）。
- PBR / 配当利回りなどバリュー指標の追加。
- execution / monitoring / strategy モジュールの具体実装と実取引・ペーパー取引向けの統合。
- 単体テスト・統合テストの充実（DuckDB を用いた fixture、OpenAI 呼び出しモックなど）。

もし CHANGELOG の項目に特定の追加情報（著者、コミットハッシュ、関連チケット等）を入れたい場合は、提供いただければ追記します。