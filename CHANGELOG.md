# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

- 今後の変更に関する未リリースの項目をここに記載します。

## [0.1.0] - 2026-04-04

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py: __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring

- 環境設定 / .env ロード機能
  - src/kabusys/config.py
    - .env と .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応
    - .env パーサ実装（コメント、export プレフィックス、引用符・エスケープ処理のサポート）
    - 上書きロジック（override, protected）を実装して OS 環境変数を保護
    - Settings クラスで以下の設定をプロパティ経由で取得
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
      - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等のパス設定
      - KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL の検証）
      - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（OpenAI を用いたニュースセンチメント）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成
    - gpt-4o-mini を JSON mode で呼び出し、銘柄ごとに -1.0〜1.0 のスコアを取得
    - バッチ処理 (最大 20 銘柄 / チャンク)、1 銘柄あたりの最大記事数・文字数トリム
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ
    - レスポンスの厳格バリデーション（JSON 抽出、results 配列検査、コード照合、数値検証）
    - スコアを ±1.0 にクリップ、部分成功に配慮した DB 書き換え（DELETE → INSERT、対象コードを絞る）
    - calc_news_window: タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST の UTC 変換）を計算

  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次の市場レジーム判定（bull/neutral/bear）を実装
    - prices_daily, raw_news, market_regime テーブルを使用
    - マクロニュースはマクロキーワードでフィルタリングして LLM に渡す
    - OpenAI 呼び出しに対するリトライ/フォールバック（失敗時 macro_sentiment = 0.0）
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None／中立扱い）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（データ不足時は None）
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（EPS が 0/欠損の場合は None）
    - DuckDB を用いた SQL ベースの実装（外部 API 呼び出し無し）
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（存在しない場合は None）
    - calc_ic: スピアマンのランク相関（IC）計算（欠損/少数レコード時は None）
    - rank: 平均ランクを返すユーティリティ（round で丸めて ties を安定化）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
  - src/kabusys/research/__init__.py で主要関数を公開

- データプラットフォーム / ETL / カレンダー管理
  - src/kabusys/data/calendar_management.py
    - market_calendar による営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動
    - calendar_update_job: J-Quants から差分取得 → 冪等保存、バックフィルと健全性チェック実装
    - 最大探索日数／ルックアヘッド／バックフィル等の定数と安全対策
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラーなどを保持）
    - 差分更新、backfill、品質チェック（quality モジュール）に対応する設計（jquants_client 経由で保存）
    - DuckDB テーブル存在チェックや最大日付取得等のユーティリティ
  - src/kabusys/data/__init__.py と jquants_client / quality との連携を想定

- インフラ・実装上の設計方針／安全対策
  - 全モジュールでルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しない設計
  - DuckDB を中心に SQL と Python の組合せで計算・保存を行う
  - 外部 API 呼び出し（OpenAI, J-Quants 等）は失敗時にフェイルセーフ（ロギングして 0/中立値で継続）するよう実装
  - API 呼び出しは明示的なリトライと指数バックオフを採用
  - DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT）とトランザクションで保護
  - テスト容易性を考慮した _call_openai_api の差し替え可能設計（unittest.mock.patch を想定）

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 環境変数の読み込みで OS 上の既存環境変数を保護する仕組み（protected set）を導入。
- API キーは明示的に引数で注入可能（テスト時の差し替えや環境依存を低減）。

---

注記:
- 本 CHANGELOG は提供されたコードベースの内容と実装コメントから推測して作成しています。機能の挙動や外部依存（J-Quants / OpenAI）の実際の詳細は実行環境や外部サービスの仕様に依存します。