# Changelog

すべての変更は Keep a Changelog の規約に従って記載します。  
現在のバージョン: 0.1.0 (初回公開)

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加内容・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境変数 / 設定管理
  - `kabusys.config.Settings` を追加。環境変数から設定値を取得するプロパティ API を提供（J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等）。
  - 自動 `.env` ロード機能を実装:
    - プロジェクトルート判定に `.git` または `pyproject.toml` を使用（`_find_project_root`）。
    - ルートが特定できる場合、自動で `.env`（低優先）と `.env.local`（高優先）を読み込み。OS 環境変数は保護（上書き防止）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを無効化可能。
  - `.env` パーサーの強化（`_parse_env_line`）:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォート有無での区別）に対応。

- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp.score_news` を追加:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでバッチ解析して ai_scores テーブルに書き込む。
    - 機能: タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST → UTC に変換）、記事トリム（銘柄あたり最大記事数・文字数制限）、バッチサイズ 20、レスポンスバリデーション、スコアクリップ（±1.0）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。リトライ不可/不正レスポンスはスキップして継続（フェイルセーフ）。
    - テスト向けの差し替えポイント（`_call_openai_api`）を用意。
    - DuckDB の executemany に対する互換性配慮（空リストは実行しない）。
  - `kabusys.ai.regime_detector.score_regime` を追加:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（'bull' / 'neutral' / 'bear'）を日次判定。
    - マクロキーワードで raw_news をフィルタし、最大 20 件のタイトルを LLM で評価（gpt-4o-mini、JSON mode）。
    - レジーム合成ロジックと閾値（bull/bear のしきい値 0.2）、スコアクリップ、失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - DB へ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。

- データ関連（Data Platform）
  - `kabusys.data.pipeline.ETLResult` と ETL パイプライン補助機能を追加:
    - 差分取得・保存・品質チェックフローを想定した結果オブジェクト（品質問題リスト、エラー一覧、保存件数等）。
  - `kabusys.data.calendar_management` を追加:
    - JPX マーケットカレンダー管理（market_calendar テーブルの夜間バッチ更新 `calendar_update_job`、営業日判定/is_trading_day/next_trading_day/prev_trading_day/get_trading_days/is_sq_day 等）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - カレンダー先読み、バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - J-Quants クライアントを用いた差分取得と冪等保存を想定。

- リサーチ（ファクター計算 / 特徴量探索）
  - `kabusys.research.factor_research`:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）などのファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。DuckDB SQL を用いた実装。
    - データ不足時には None を返すなど安全に動作。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を追加。
    - 外部依存を避け、標準ライブラリ + DuckDB で実装。
  - `kabusys.research.__init__` で主要関数を再エクスポート。

- その他ユーティリティ
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

### Changed
- 設計上の重要な方針を明文化・実装:
  - すべての分析系処理（ニューススコアリング / レジーム判定 / ファクター計算 / 将来リターン）は datetime.today()/date.today() に依存しない（外部から target_date を与えることでルックアヘッドバイアスを防止）。
  - OpenAI 呼び出しの失敗は致命化させず、部分失敗時には他のデータを保護する（部分的に書き換えない / ロールバック戦略）。
  - DuckDB 特有の挙動（executemany の空リスト不可など）に合わせた実装の工夫。

### Fixed
- （初回リリースのため該当なし。設計上のフォールバックやログ出力により実装の堅牢性を高める対策を多数実施。）

### Security
- 環境変数の読み込みで OS 環境変数を保護する仕組みを導入（`.env` の自動ロードで既存 OS 環境変数を上書きしない / `.env.local` は override だが protected set を考慮）。
- OpenAI API キーは明示的に引数または環境変数 `OPENAI_API_KEY` から解決し、未設定時には明確なエラーを出す。

### Internal / Testing
- OpenAI 呼び出し部分に差し替えフック（`_call_openai_api`）を用意し、ユニットテストでモック可能。
- レスポンスパースや DB ロールバック失敗時のログを充実させ、運用時のトラブルシュートを容易に。

---

参照: この CHANGELOG はソースコードの内容（モジュール構成・関数・定数・設計コメント）から推測して作成しています。実際のリリースノートには追加の運用上の注意や API 互換情報を含めることを推奨します。