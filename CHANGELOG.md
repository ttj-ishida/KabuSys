# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。

なお本リポジトリの初回リリース（0.1.0）はコードベースから推測して作成しています。

## [Unreleased]


## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能をパッケージ化しました。以下はコードベースから推測できる主な追加点・設計方針・既知の制約です。

### Added
- パッケージ基礎
  - パッケージ初期化 (src/kabusys/__init__.py)、バージョン: 0.1.0、公開モジュール: data, strategy, execution, monitoring。
- 設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサ (.env の export 形式、クォートやインラインコメントの扱いに対応)。
    - Settings クラス: 必須キー取得 (_require)、型変換（Path）、環境/ログレベルのバリデーション、便利なブールプロパティ（is_live 等）。
- Data レイヤー（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 冪等的保存機能（DuckDB への ON CONFLICT / DO UPDATE を使用する save_* 関数）。
    - ページネーション対応、リトライ（指数バックオフ、最大3回、408/429/5xx の取り扱い）。
    - 401 発生時の ID トークン自動リフレッシュと1回の再試行をサポート。
    - データ整形ユーティリティ（_to_float, _to_int）と fetched_at の UTC 記録（Look-ahead バイアス対策）。
- Data レイヤー（ニュース収集）
  - src/kabusys/data/news_collector.py:
    - RSS フィード収集パイプライン（URL 正規化、トラッキングパラメータ除去、テキスト前処理）。
    - 記事ID の生成に SHA-256（正規化後のハッシュ上位）を使用して冪等保存を実現。
    - defusedxml を使った XML パース（XML Bomb などへの対策）。
    - SSRF/不正スキーム対策の考慮、受信サイズ上限（10MB）でメモリ DoS を低減。
    - DB へのバルク挿入（チャンク化）とトランザクション集約。
- Research（因子計算・分析）
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value 等のファクター計算関数 (calc_momentum, calc_volatility, calc_value)。
    - DuckDB を用いた SQL ベースの効率的なウィンドウ集計。
    - 欠損・十分なデータ件数のチェック（ウィンドウサイズ不足時は None を返す）。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、rank ユーティリティ。
    - pandas 等に依存しない純標準ライブラリ実装を意図。
  - src/kabusys/research/__init__.py に主要ユーティリティをエクスポート。
- Strategy（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py:
    - 研究で算出した raw ファクターをマージしてユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定列を Z スコア正規化 (kabusys.data.stats.zscore_normalize を利用)、±3 でクリップ。
    - features テーブルへ日付単位で冪等アップサート（トランザクションで原子性確保）。
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - 重みの受け取り（デフォルト重みで合計が 1 でない場合は再スケール）、無効な重みは警告スキップ。
    - Bear レジーム判定（AI の regime_score の平均が負 → BUY を抑制、ただしサンプル数閾値あり）。
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス / スコア低下）を生成し signals テーブルへ日付単位で置換。
- DB 操作のトランザクション処理、ログ出力、警告の追加
  - 各種関数で BEGIN/COMMIT/ROLLBACK を用いて原子性を確保。
  - ロギングにより状態・異常を記録（例: ROLLBACK 失敗警告、価格欠損による SELL 判定スキップ等）。

### Changed
- （初回リリースのため「変更」はありません）

### Fixed
- （初回リリースのため「修正」はありません）

### Security / Safety
- news_collector で defusedxml を使用し XML 攻撃を防止。
- RSS のダウンロードで受信サイズを制限（MAX_RESPONSE_BYTES = 10MB）。
- J-Quants クライアントでトークン管理・リフレッシュロジックにより認証ループや無限再帰を回避。
- .env ローダーは OS 環境変数の上書きを保護する仕組み（protected set）を備える。

### Known limitations / TODOs
- signal_generator において、Trailling stop（ピークからのトレーリングストップ）および時間決済（保有日数閾値）は未実装。positions テーブルに peak_price / entry_date 等が必要。
- 一部の集計はウィンドウサイズ不足時に None を返す仕様（データ不足取り扱いは意図的だが、エンドツーエンドの動作確認が必要）。
- execution 層（発注・kabuステーション API 統合）は空のパッケージディレクトリが定義されているのみで実装は別途（src/kabusys/execution/__init__.py は空）。
- tests や CI に関する記載はコードからは確認できないため別途整備推奨。
- 外部依存（defusedxml、duckdb）は runtime 環境で正しくインストールされていることが前提。

---

参考: 本 CHANGELOG はリポジトリ内のソースコード（主に docstring と実装）から推測して作成しています。実際の変更履歴やリリースノートを作成する際はコミット履歴（git log）・リリース管理情報を優先してください。