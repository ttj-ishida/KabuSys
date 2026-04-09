# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、提示されたコードベースの内容から実装・仕様を推測して作成しています。

全般的な方針:
- DuckDB / SQLite を利用したローカルデータ処理中心（外部売買 API への直接アクセスは限定的）。
- ルックアヘッドバイアス（未来データ参照）を避ける設計が随所に反映されている。
- OpenAI（gpt-4o-mini）連携部分はフェイルセーフ設計（リトライ・フォールバック）を採用。

※ 日付はこの CHANGELOG 作成日（2026-04-09）を使用しています。

## [Unreleased]
- ドキュメントやテストの追加、マスタデータ（銘柄ごとの lot_size 等）対応の拡張などが予定されています。
- prices_daily / raw_financials 等のデータ品質フォールバック（前日終値・取得原価など）に関する改善案あり（コード内 TODO）。

## [0.1.0] - 2026-04-09

### Added
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"`。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護（protected keys）され、.env の上書きを防止。
  - .env パーサを実装（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - 必須環境変数取得用ユーティリティ `_require` を実装（未設定時は ValueError を送出）。
  - `Settings` クラスを追加し、次のプロパティを提供:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト値あり）
    - LINE API: `line_channel_access_token`, `line_user_id`（任意）
    - DB パス: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`（Path 化して `expanduser()` 適用）
    - Paper Trading: `paper_fill_mode`（値検証: instant/partial/never/reject）
    - 監視: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - システム: `env`（development/paper_trading/live の検証）、`log_level`（DEBUG/INFO/... の検証）、`is_live/is_paper/is_dev` のショートカット

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定 / 重み計算（純粋関数群、DB 非参照）
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（各重み = 1/N）。
    - calc_score_weights: スコア加重配分。全銘柄のスコア合計が 0 の場合は等金額にフォールバックし WARNING ログを出力。
  - リスク調整（セクター上限・レジーム乗数）
    - apply_sector_cap: 既存保有のセクター別時価を計算し、1セクター上限を超える場合は同セクターの新規候補を除外（"unknown" セクターは除外対象外）。当日売却予定銘柄を計算から除外可。
    - calc_regime_multiplier: 市場レジーム文字列（'bull'/'neutral'/'bear'）を乗数（1.0/0.7/0.3）に変換。未知レジームは警告を出して 1.0 にフォールバック。
  - ポジションサイズ算出（calc_position_sizes）
    - allocation_method に応じて株数計算を実装（"risk_based", "equal", "score"）。
    - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく算出。
    - equal/score: ウェイトに基づく割当。per-position 上限、aggregate cap、lot_size（単元株）丸めに対応。
    - aggregate cap 超過時はスケールダウンし、余剰キャッシュで残差分を lot 単位で再分配（再現性のため安定ソート順）。
    - cost_buffer による手数料/スリッページの保守的見積りを考慮。

- リサーチ / ファクター（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。必要行数未満は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials（EPS, ROE）を用いて PER / ROE を計算。財務データは target_date 以前の最新レコードを使用。
    - いずれも DuckDB SQL を用いた実装（prices_daily / raw_financials を参照）。返り値は (date, code) を含む dict のリスト。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。horizons の検証あり（1〜252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。有効レコードが 3 件未満の場合は None。
    - rank: 同順位は平均ランクを採るランク変換。浮動小数丸めで ties 対応。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

- AI（OpenAI）関連（src/kabusys/ai/*）
  - news_nlp (ニュース NLP スコアリング)
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST → UTC 変換）を提供。
    - score_news: raw_news と news_symbols を集約し、最大 N 銘柄ずつ（_BATCH_SIZE）で OpenAI API（gpt-4o-mini）にバッチ送信してセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む。
      - 銘柄ごとの記事数と文字数を制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - API 呼び出しはリトライ（429・ネットワーク断・タイムアウト・5xx を対象）を行い、失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
      - レスポンスの JSON 検証と型チェックを行い、スコアを ±1.0 にクリップ。
      - DB 書き込みは部分的な上書き（対象コードのみ DELETE→INSERT）で冪等性・部分失敗耐性を確保。DuckDB executemany の空パラメータ制約に配慮。
      - API キーは引数または環境変数 `OPENAI_API_KEY` から解決（未設定時は ValueError）。
  - regime_detector (市場レジーム判定)
    - score_regime: ETF 1321（日経連動 ETF）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ記録する。
      - MA200 乖離は target_date 未満データのみを使用（ルックアヘッド回避）。データ不足時は中立（1.0）でフォールバック。
      - マクロニュースはキーワード検索でタイトルを抽出し、OpenAI でマクロセンチメントを取得（記事がない場合は LLM 呼び出し不要、フォールバック 0.0）。
      - 合成スコアは重み付け（MA70% / macro30%）、閾値により label を 'bull'/'neutral'/'bear' に分類。
      - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。API キー解決は news_nlp と同様。
      - LLM 呼び出し関数は news_nlp と独立実装（モジュール結合回避）。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite で複数テーブルとインデックスを作成する冪等関数を実装。
    - system_status, trade_logs, positions, risk_logs 等のテーブル定義とインデックス作成を含む（監視 / ロギング用スキーマ）。

- パッケージエクスポート
  - portfolio・research・ai の主要関数を __all__ で公開。

### Changed
- （初版のため履歴的変更はなし。設計コメントとして将来的な拡張点を多数コメントに記載）
  - 各モジュールに設計意図・制約・フォールバック（例: 価格欠損時の挙動、DuckDB バインドの注意点、テスト用フック）を明示。

### Fixed
- （初版のため明確なバグ修正履歴はなし。ただし実装上の安全策・ログ出力（Warning/Debug）を充実させている）

### Security
- OpenAI API キーは引数または環境変数から解決。未設定時は例外（ValueError）で明示。
- .env 自動ロードで OS 環境変数を保護（上書き禁止）する実装を採用。

### Removed / Deprecated
- なし（初版）

---

参考: 実装内の注意点・既知の制約
- .env パーサは多くのケースに対応しているが、極端なネストや複雑なシェル展開は未対応。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map を受け取る拡張予定）。
- price が欠損（0.0）の場合、exposure や position size の見積が過小評価される可能性があり、将来的に前日終値等でのフォールバックを検討する旨がコード内に TODO コメントあり。
- DuckDB の executemany に関する互換性問題への対処（空リストチェック等）は実装済み。
- LLM の出力バリエーション（余分なテキスト等）に対する耐性処理（最外の {} を抽出して JSON パースを試みる等）を行っているが、確実性を要する環境では追加のバリデーションを推奨。

この CHANGELOG はソースコードから推測して作成したため、実際のコミット履歴やリリースノートと差分がある可能性があります。必要であれば、個々の関数・挙動に基づくより詳細な変更点（想定ユースケース、入出力例、制限事項など）を追加します。