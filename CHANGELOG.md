# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に従います。  
安定リリース、互換性、変更の種類（Added / Changed / Fixed / Deprecated / Removed / Security）を明確に記載します。

なお、本CHANGELOGはリポジトリ内のコード内容から推測して作成しています。

## [Unreleased]

- 次回リリースに向けた変更点をここに記載します。

## [0.1.0] - 2026-04-01

初回公開リリース。以下の主要機能を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン定義（__version__ = "0.1.0"）。
  - サブパッケージ公開: data, research, ai, execution, monitoring, strategy（__all__ により一部モジュールを公開）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）で CWD に依存しない読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 柔軟で堅牢な .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどに対応）。
  - override と protected オプションにより OS 環境変数の保護や上書きを制御。
  - Settings クラスを提供し、各種必須オプションをプロパティ経由で取得:
    - J-Quants / kabu ステーション / Slack トークン・チャンネル、データベースパス（duckdb/sqlite）、監視閾値（CPU/MEM/DISK）、PID ファイルパス、実行環境（development/paper_trading/live）、ログレベル等。
    - 必須環境変数未設定時は明確な ValueError を送出。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON mode を用いてバッチでセンチメントを評価。
  - 時間ウィンドウ計算（JST基準で前日15:00 ～ 当日08:30 に対応、内部は UTC naive datetime を使用）。
  - バッチ処理、チャンクサイズ制御（_BATCH_SIZE=20）、1銘柄あたりの記事数・文字数制限によるトークン肥大対策。
  - API 呼び出しでのリトライ（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）とフォールバック挙動。
  - レスポンスの厳密な検証処理（JSON 抽出、results リスト検査、コード照合、数値検証、±1.0 クリップ）。
  - DuckDB への冪等的な書き込み処理（対象コードのみ DELETE → INSERT）を実装。
  - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api をモック可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - ma200_ratio 計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。
  - マクロ関連記事の抽出（キーワードベース、最大 N 件）。
  - OpenAI を用いたマクロセンチメント評価（JSON mode、リトライ、失敗時は macro_sentiment=0.0 のフェイルセーフ）。
  - レジーム合成ロジック（スコアクリップ、閾値でラベル付け）、市場レジームテーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - API キー未設定時の明示的エラー。

- 研究用ファクター・特徴量探索（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の算出（データ不足時の扱い明確化）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の算出。
    - calc_value: raw_financials からの EPS/ROE を使った PER/ROE 計算（PBR 等は未実装）。
    - 計算は DuckDB 上の SQL と Python 結合で実行し、prices_daily/raw_financials のみを参照（発注 API にはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的クエリ実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（欠損・同値処理・十分サンプル判定あり）。
    - rank: 平均ランク（同順位は平均ランク）を返す実装（丸めによる ties 対策あり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - 追加ユーティリティ: data.stats の zscore_normalize を再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存。
  - pipeline:
    - ETLResult データクラスを提供（ETL の取得件数、保存件数、品質問題、エラー等を集約）。
    - 差分更新、backfill の考慮、品質チェック（quality モジュール）を考慮した設計（外部 API 呼び出しは jquants_client を経由）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 設計方針・品質
  - ルックアヘッドバイアス防止のため、date.today()/datetime.today() を参照しない設計（target_date を引数に取る）。
  - OpenAI 呼び出しや外部依存の失敗時はフェイルセーフで継続する（可能な限り例外を伝播させずログに記録）。
  - DuckDB に対して互換性を考慮した実装（executemany の空リスト制約等への対応）。
  - ロギングを広く配置して実行時の可観測性を確保。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 環境変数の必須チェック（API キーやトークンが未設定の場合は ValueError を送出）により、誤設定に早期に気付けるように実装。

---

注意事項（既知の制約・今後の改善候補）
- OpenAI SDK のバージョン差異（例: APIStatusError/ status_code の有無）を考慮した防御的実装になっていますが、将来的に SDK の仕様変更に追従する必要があります。
- 一部関数は DuckDB のバージョン依存の挙動（配列バインドや executemany の制約）を考慮して実装されています。DuckDB バージョンを上げた際の挙動確認が必要です。
- calc_value は現時点で PBR や配当利回りを未実装。必要に応じて拡張予定です。
- jquants_client（外部クライアント）や quality モジュールの実装詳細に依存するため、本リリースではそれらの実装と接続テストが必要です。

（このCHANGELOGはコードベースの内容から推測して生成しています。実際の変更履歴・公開ノートはリポジトリのコミット履歴やリリースノートと照合して調整してください。）