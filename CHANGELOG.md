# Changelog

すべての注目すべき変更点を記録します。このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従います。バージョン番号はセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムの基盤機能（設定管理、データ ETL・カレンダー管理、リサーチ用ファクター計算、AI ベースのニュース解析・市場レジーム判定等）を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__`（バージョン: 0.1.0、公開モジュール一覧の定義）。
- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動ロード機能を実装（プロジェクトルート判定は `.git` または `pyproject.toml` を使用）。
  - .env のパースロジックを独自実装（コメント、`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード抑制用環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 設定取得用 `Settings` クラスを実装。プロパティ経由で以下を取得:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB, SQLite）など。
  - 必須環境変数チェックを行い、未設定時に分かりやすいエラーメッセージを返す。
  - `KABUSYS_ENV` の値検証（`development` / `paper_trading` / `live`）、`LOG_LEVEL` の検証（`DEBUG`/`INFO`/…）。
- AI モジュール
  - `kabusys.ai.news_nlp`:
    - 生ニュース (`raw_news`, `news_symbols`) を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント評価して `ai_scores` テーブルへ書き込む機能を実装。
    - ニュース収集ウィンドウは JST 前日 15:00 〜 当日 08:30（UTC に変換）で定義。`calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数・文字数上限でプロンプト肥大を防止。
    - OpenAI の JSON モードを利用し、レスポンスのバリデーション・スコアの ±1.0 クリップを実装。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライや、非リトライエラーのフェイルセーフ（スキップして継続）を実装。
    - DuckDB の互換性（executemany の空リスト制約）に配慮した安全な DB 書き込み（DELETE → INSERT、トランザクション）を実装。
  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（`bull`/`neutral`/`bear`）を判定し、`market_regime` テーブルへ冪等書き込みを行う機能を実装。
    - マクロキーワードでニュースを抽出し、OpenAI に投げて JSON レスポンスをパース。
    - API リトライ・フォールバック（失敗時は macro_sentiment=0.0）を実装。レスポンスパース失敗時にも例外を投げず 継続する設計。
    - ルックアヘッドバイアス対策として、内部処理で `datetime.today()` / `date.today()` を参照しない設計。クエリでは `date < target_date` を厳守。
- データ関連 (`kabusys.data`)
  - `calendar_management`:
    - JPX カレンダー管理機能を実装。market_calendar テーブルの有無を考慮した営業日判定、前後の営業日の取得、期間内営業日の列挙、SQ 日判定等のユーティリティを提供。
    - DB にデータがない場合は曜日ベース（土日を非営業日）でフォールバック。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants API から差分取得し冪等保存、バックフィル、健全性チェック）。
  - ETL パイプライン (`kabusys.data.pipeline` / `kabusys.data.etl`):
    - ETL のための `ETLResult` データクラスを実装（取得/保存件数、品質チェック結果、エラーなどを集約）。
    - 差分取得・バックフィル・品質チェックを担う ETL 設計を反映（詳細実装のためのインタフェース）。
    - J-Quants クライアント（`jquants_client`）との連携を想定。
- リサーチ (`kabusys.research`)
  - ファクター計算 (`factor_research`):
    - モメンタム: 約1ヶ月/3ヶ月/6ヶ月リターン、200日移動平均乖離を算出する `calc_momentum` を実装（DuckDB SQL ベース）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを算出する `calc_volatility` を実装。
    - バリュー: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出する `calc_value` を実装。
  - 特徴量探索 (`feature_exploration`):
    - 将来リターン計算（`calc_forward_returns`。デフォルト horizons=[1,5,21]）を実装。ホライズンは検証済みの整数制約あり。
    - IC（Information Coefficient）計算（Spearman の ρ）を行う `calc_ic` を実装。
    - 値をランクに変換する `rank`、ファクター統計サマリーを返す `factor_summary` を実装。
  - `kabusys.research.__init__` で主要関数を再エクスポート。
- モジュールエクスポート
  - 主要モジュールで __all__ を整備（例: ai, research, data.etl 等）。

### 変更 (Changed)
- （初回リリースにつき相対的な「変更」はなし。設計上の決定や仕様は実装ドキュメント風の docstring に反映済み）

### 修正 (Fixed)
- （初回リリースにつきバグ修正履歴なし）

### 注記 / マイグレーション (Notes / Migration)
- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（各機能を使う場合）。
  - DB パスはデフォルトで `data/kabusys.duckdb`（DuckDB）と `data/monitoring.db`（SQLite）を使用。`DUCKDB_PATH` / `SQLITE_PATH` で上書き可能。
  - OpenAI API は環境変数 `OPENAI_API_KEY` または各 API 関数の `api_key` 引数で指定。未設定時は ValueError を送出する。
  - 自動 .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- データベース互換性
  - DuckDB における `executemany` の空リストバインドの制約へ配慮した実装を行っています（空パラメータの場合は実行しない）。
- フェイルセーフ挙動
  - AI 関連の一時エラーやレスポンスパース失敗は基本的にフェイルセーフ（スコア 0.0 や該当銘柄スキップ）で処理を継続します。これにより部分的な外部サービス障害がシステム全体を停止させるのを防止します。
- ルックアヘッドバイアス対策
  - すべての分析関数（ニュース/レジーム/ファクター計算等）は明示的な `target_date` を受け取り、内部で `date.today()` を参照しない設計になっています。

### 依存関係（主な外部ライブラリ）
- duckdb
- openai（OpenAI SDK）
- 標準ライブラリ（datetime, json, logging など）

### 既知の制限 (Known limitations)
- 現時点で PBR・配当利回りなど一部バリューファクターは未実装（注記あり）。
- News/Regime の LLM 呼び出しは gpt-4o-mini を想定しているため、将来的なモデル変更時にプロンプトやレスポンスパースの調整が必要な場合があります。
- `jquants_client` や `quality` モジュールの実装詳細（API 呼び出しや品質判定ルール）は本リリースで想定インタフェースを利用しています。実環境での接続時はクライアント実装を用意してください。

---

今後のリリースでは、実稼働向けのモニタリング／自動発注（execution）・監視（monitoring）モジュールの追加、テストカバレッジ拡充、パフォーマンス最適化を予定しています。