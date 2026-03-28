# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

※この変更履歴は提供されたソースコードの内容から推測して作成しています。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### Added
- パッケージ初期設定
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を設定。
  - パッケージの公開 API に `data`, `strategy`, `execution`, `monitoring` を宣言。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、CWD に依存しない実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env 解析機能を強化:
    - `export KEY=val` 形式、シングル/ダブルクォート対応、バックスラッシュエスケープ対応、行内コメント処理などに対応。
  - `Settings` クラスを提供し、明示的プロパティで各種設定値を取得可能:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - 必須環境変数未設定時は分かりやすい ValueError を送出。

- データ管理 (`kabusys.data`)
  - ETL パイプラインの公開インターフェース `ETLResult` を実装・エクスポート（`data.pipeline`）。
  - calendar 管理 (`calendar_management`):
    - JPX カレンダーの夜間差分更新ジョブ（`calendar_update_job`）。
    - 市場営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB 未取得時は曜日ベースのフォールバック（週末 = 休場）。
    - 安全策として検索範囲制限（最大探索日数）や健全性チェックを実装。
  - ETL パイプライン (`data.pipeline`):
    - 差分更新、バックフィル、品質チェックのフレームワークを実装。
    - fetch/save は `jquants_client` を利用（差分取得 → idempotent 保存）。
    - ETL 実行結果を格納する `ETLResult` dataclass（品質問題やエラー一覧を保持）。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`):
    - 前日 15:00 JST ～ 当日 08:30 JST の記事ウィンドウを計算し、銘柄別に記事を集約して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ単位の最大銘柄数、記事/文字数トリム、JSON mode を用いた堅牢なレスポンス処理。
    - 429/ネットワーク/タイムアウト/5xx に対するエクスポネンシャルバックオフリトライ実装。
    - レスポンスのバリデーション（results リスト、code/score の型チェック、未知コード無視、スコアの ±1.0 クリップ）。
    - 成功した銘柄のみを DELETE→INSERT で置換し、部分失敗時に既存スコアを保護する戦略を採用（DuckDB 互換性考慮）。
  - 市場レジーム判定 (`regime_detector.score_regime`):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロニュース抽出・LLM 呼び出し（gpt-4o-mini）・レスポンス JSON パース・リトライ/フェイルセーフを実装。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
  - AI モジュール共通設計:
    - OpenAI 呼び出しはテスト容易性のため差し替え可能に実装（内部関数を個別に持つ）。
    - API キーは引数優先、それが無ければ環境変数 `OPENAI_API_KEY` を参照。未設定時は ValueError。

- リサーチ / ファクター群 (`kabusys.research`)
  - ファクター計算 (`factor_research`):
    - Momentum（1M/3M/6M リターン、ma200_dev）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を実装。
    - DuckDB 上の SQL を活用した効率的な実装。データ不足時は None を返す扱い。
  - 特徴量探索 (`feature_exploration`):
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の rho）計算、ランク変換、ファクター統計サマリーを実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティ群を __all__ で公開（zscore_normalize は data.stats から取得）。

### Changed
- 初回リリースのため変更履歴差分は無し（新規実装）。

### Fixed
- 初回リリースのため既存バグ修正履歴は無し。

### Security
- OpenAI API キーや各種トークンは Settings 経由で必須チェックを行い、未設定時に明示的エラーを発生させることで誤運用を防止。

### Notes / 設計上の考慮点（重要な挙動）
- ルックアヘッドバイアス対策:
  - いずれの処理（ニュース集計、レジーム判定、ファクター計算）でも内部で datetime.today()/date.today() を直接参照しない実装を採用。必ず外部から target_date を与えて処理する設計。
  - DB クエリは target_date より前のデータのみを参照するなど注意点あり。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時はデフォルト値（例: macro_sentiment=0.0）で継続し、致命的な例外を上げない設計（ただし DB 書き込み失敗などは上位に伝播）。
  - ETL の品質チェックで重大な問題が見つかっても ETL 自体は継続し、問題は ETLResult に収集して呼び出し側で処理判断する方針。
- DuckDB 互換性:
  - executemany に空リストが与えられると失敗するバージョン対応や配列バインドの回避など、DuckDB の挙動に対するワークアラウンドを実装。
- OpenAI 呼び出し:
  - JSON Mode（response_format={"type": "json_object"}）を用い、レスポンス解析時は前後の余計なテキスト混入を想定した復元処理を含む。
- DB 操作は基本的に冪等化（DELETE→INSERT や ON CONFLICT）を意識。

### Breaking Changes
- 初回リリースのため破壊的変更は無し。

### Known limitations / TODO
- strategy / execution / monitoring の具象実装はパッケージ公開面で示されているが、今回提供コードには含まれていない（将来的な実装予定）。
- PBR・配当利回り等一部バリューファクターは未実装（README/StrategyModel.md を参照する想定）。
- テスト用のモック・統合テストは別途整備が必要（OpenAI / J-Quants クライアントの外部呼び出しを伴うため）。

----

参考: 本 CHANGELOG はソースコードの実装内容・コメント・docstring から機能と挙動を推測して作成しています。必要であれば各モジュール単位でより細かい変更点や使用例、移行ガイドを追記します。