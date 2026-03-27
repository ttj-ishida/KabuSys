# Changelog

すべての重要な変更履歴をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更は意味のある単位でまとめ、可能な限り関数名／モジュール名を明示しています。
- 日付はリリース日の想定（本リポジトリ内の __version__ = "0.1.0" に対応）です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能・モジュールを含みます。

### Added
- パッケージ初期化
  - pakage: kabusys
  - __version__ = "0.1.0"
  - パブリック API: data, strategy, execution, monitoring を __all__ として公開（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml により検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパーサ実装（クォート、エスケープ、inline コメント、export 形式対応）。
  - 環境変数保護（OS 環境変数を protected として .env.local の上書きを制御）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティ（必須キーは _require により未設定時に ValueError を送出）。
    - env/log_level のバリデーション（許容値: development|paper_trading|live、ログレベルは DEBUG/INFO/...）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに gpt-4o-mini を用いたセンチメントスコアを取得。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で計算。
    - バッチ処理（最大 20 銘柄／API 呼び出し）・トリム（最大記事数/文字数）・リトライ（指数バックオフ）に対応。
    - API レスポンスの厳密検証（JSON mode + レスポンス復元ロジック）、スコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE→INSERT、部分失敗時に他銘柄を保護）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テスト性を考慮し、内部の API 呼び出し関数は差し替え可能（unittest.mock.patch 対応箇所あり）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロニュースは news_nlp.calc_news_window を利用して窓を算出、raw_news からマクロキーワードでフィルタ。
    - OpenAI 呼び出し（gpt-4o-mini）に対する堅牢なリトライ/フォールバック（API失敗時は macro_sentiment=0.0）。
    - DB へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データ系（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定ユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90)（J-Quants から差分取得 → 保存）。
    - バックフィル、健全性チェック、検索上限（日数制限）などの安全対策を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（target_date, fetched/saved 件数, quality_issues, errors 等を含む）。
    - 差分取得、保存（jquants_client を経由して冪等保存）、品質チェックの設計。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

  - その他ユーティリティ:
    - DuckDB テーブル存在チェック、最大日付取得などヘルパー実装。

- リサーチ系（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日移動平均乖離(ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB ベースの SQL 実装で外部 API にはアクセスしない。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（例: 翌日/翌週/翌月）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。
    - rank(values): 同順位は平均ランクで処理するランク関数（丸め対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
    - 研究用途に適した純粋計算ユーティリティ群（標準ライブラリのみで実装）。

- 再エクスポート・パッケージ層
  - research パッケージで主要関数を __all__ にて公開（calc_momentum 等、zscore_normalize の再利用など）。
  - ai パッケージで score_news を公開。

### Changed / Design decisions
- ルックアヘッドバイアス対策
  - AI モジュールおよびリサーチ関数は内部で datetime.today()/date.today() を参照しない実装（target_date を明示的に受け取る）。
  - DB クエリは target_date 未満／以前等の排他条件でルックアヘッドを防止。

- フェイルセーフ設計
  - OpenAI API 呼び出しでの失敗（429/ネットワーク/タイムアウト/5xx）に対して指数バックオフでリトライし、最終的にフォールバック値（0.0 等）で継続する方針。
  - DuckDB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。部分失敗時に既存データを不用意に消さない戦略（対象コードの絞り込み DELETE→INSERT）。

- テスト性の向上
  - OpenAI 呼び出しをラップした内部関数（_call_openai_api）をモック差し替え可能にしてユニットテストを容易に。

### Fixed / Robustness improvements
- .env パースの強化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、inline コメント判定の厳密化。
  - ファイル読み込み失敗時は warnings.warn を発行して無効化する挙動。

- OpenAI レスポンスパースの堅牢化
  - JSON mode を利用しつつ、稀に前後に余計なテキストが混ざるケースに対して外側の最初と最後の {} を抽出して復元する処理を追加。
  - レスポンス検証ルールを厳密化（キー存在/型チェック/既知コードの照合/数値検査）。

- データ不足時の安全なデフォルト
  - ma200 等の計算でデータ不足の場合、中立値（1.0 や None）を返して処理継続する実装。

### Known limitations / Notes
- OpenAI API キーは score_news / score_regime の引数で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出する。
- DuckDB との互換性に依存する箇所（executemany 空リストの回避等）を考慮した実装になっている。
- 一部の財務指標（PBR・配当利回り等）は未実装（calc_value の注釈参照）。

---

以上が初回リリース（0.1.0）の主な変更点・実装内容です。必要であれば各モジュールの関数一覧や使用例（設定・DB スキーマ期待値・実行フロー）を別途まとめます。