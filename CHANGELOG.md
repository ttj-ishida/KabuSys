# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

注意: 本 CHANGELOG は与えられたコードベースから推測して作成した初回リリース向けの記述です。

## [Unreleased]

## [0.1.0] - 2026-04-03

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加。バージョンは `0.1.0`。
  - パッケージの公開 API: data, strategy, execution, monitoring を `__all__` で定義。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み:
    - プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` と `.env.local` を読み込む。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護する protected セットを導入し、override 時に上書きしない。
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーは以下に対応:
    - 空行・コメント（#）スキップ、`export KEY=val` 形式、シングル/ダブルクォート値とバックスラッシュエスケープ、インラインコメントの扱い等。
  - 必須設定取得ヘルパー `_require` と、J-Quants / kabu / LINE / DB /監視系の設定プロパティを実装。
  - 環境値の検証: `KABUSYS_ENV` および `LOG_LEVEL` に対する許容値チェックを実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメントを算出して `ai_scores` テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄当たり最大 10 記事・3000 文字でトリム。
    - 再試行/バックオフ: 429/ネットワーク切断/タイムアウト/5xx をエクスポネンシャルバックオフでリトライ。
    - レスポンスの堅牢なバリデーションと ±1.0 のクリップ。
    - API 呼び出し箇所をユニットテストで差し替え可能（_call_openai_api を patch 可能）。
    - エラー時はフェイルセーフにより該当チャンクをスキップし、他銘柄のスコアを保護（部分失敗に強い設計）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して `'bull' / 'neutral' / 'bear'` を日次で判定。
    - 処理フロー:
      - 1321 の ma200 比率計算（target_date 未満のデータのみ使用、ルックアヘッド防止）。
      - マクロキーワードでフィルタしたニュースタイトルを抽出し、OpenAI に渡してマクロセンチメントを算出。
      - スコア合成後、`market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 失敗時は macro_sentiment=0.0 にフォールバックし処理継続。
    - OpenAI 呼び出しは分離実装で、テスト容易性を考慮。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新、保存（idempotent）、品質チェックの土台実装。
    - ETL 実行結果を表す `ETLResult` dataclass を導入（to_dict による品質問題のシリアライズ対応）。`kabusys.data.etl` で再エクスポート。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ（market_calendar テーブル）を実装。
    - 営業日判定: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - 夜間バッチ更新 job: `calendar_update_job`（J-Quants から差分取得して保存、バックフィル、健全性チェックを実装）。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日扱い）。
    - 最大探索幅やバックフィル日数などの安全ガードを実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR, 相対 ATR, 平均売買代金, 出来高比率）、Value（PER, ROE）を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースの計算を行う。
    - 入力は prices_daily / raw_financials に限定（外部 API に依存しない設計）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 (`calc_forward_returns`)：任意ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC 計算 (`calc_ic`)：スピアマンランク相関を実装（同順位は平均ランク）。
    - ランク化ユーティリティ (`rank`)、統計サマリー (`factor_summary`) を提供。
  - research パッケージの public API を __all__ で整理。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 環境変数に以下の機密値が必要／利用されます:
  - `OPENAI_API_KEY`（OpenAI 呼び出し。news/regime で使用）
  - `JQUANTS_REFRESH_TOKEN`（J-Quants API）
  - `KABU_API_PASSWORD`（kabu ステーション API）
- `.env` 自動読み込みの挙動に注意: OS 環境変数は上書きされず保護されるが、`.env.local` はデフォルトで `.env` より優先される点に注意してください。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

### Notes / 実装上の重要な設計・挙動
- ルックアヘッドバイアス回避:
  - 全ての AI/データ処理モジュールは内部で `datetime.today()` / `date.today()` を直接参照せず、必ず `target_date` を明示的に受け取る設計。
  - DB クエリは target_date 未満 / 半開区間等で厳密にデータ範囲を制御。
- OpenAI 呼出しの堅牢化:
  - JSON モードを利用しつつ、パース失敗時は前後の余計なテキストを抽出するフォールバックロジックを実装。
  - レートリミットやサーバー一時障害に対して指数バックオフでリトライ。リトライ失敗時はログ出力の上フェイルセーフ（スコア 0.0 もしくはチャンクスキップ）。
  - API 呼び出し部分はテスト時に差し替え可能（patch 対応）。
- DB 書き込みは冪等性を重視:
  - market_regime / ai_scores 等は該当日・該当銘柄分を DELETE → INSERT 形式で置換し、部分失敗時に既存データの不必要な削除を避ける工夫を実装。
  - DuckDB の executemany の制約（空リスト不可）に対応したガードを実装。
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
  - PID / Kill flag のデフォルトパスも設定あり（data/execution.pid, data/kill.flag）。
- ログレベル・環境検証:
  - `KABUSYS_ENV` は development / paper_trading / live のいずれかのみ許容。
  - `LOG_LEVEL` は標準ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）のみ許容。

### Known issues / Limitations
- 一部のファクター（PBR・配当利回り）は未実装（calc_value で注記あり）。
- News/NLP の JSON mode でも LLM によっては稀に前後付帯テキストが混入するため、パースのフォールバックを入れているが完璧ではない。
- DuckDB バインドの互換性（list 型のバインド等）に起因する実装上の注意点がある（空リストの executemany を避ける等）。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存するため、API 側の仕様変更は影響する可能性がある。

---

今後のリリースでは、使い勝手改善（設定のドキュメント化、CLI/管理用ユーティリティ）、追加ファクター・バックテスト連携、より堅牢なエラーハンドリングやメトリクス収集を予定しています。