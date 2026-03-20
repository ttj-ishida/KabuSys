Keep a Changelog
すべての変更はセマンティックバージョニングに従います。  
このファイルはコードベースから推測して作成した変更履歴です。

Unreleased
- なし

0.1.0 - 2026-03-20
Added
- パッケージ初期リリース: kabusys (日本株自動売買システム) を追加。
  - パッケージエントリーポイント: src/kabusys/__init__.py にて version=0.1.0、サブモジュールを公開。
- 環境設定読み込み機能 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env 解析器を実装（コメント行、export プレフィックス、クォーテーション・エスケープ、インラインコメントの扱いに対応）。
  - .env.local は既存の OS 環境変数を保護しつつ上書き可能（protected set を使用）。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル等）。
  - 自動読み込みを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
- データ取得・保存モジュール (src/kabusys/data)
  - J-Quants クライアント (jquants_client.py)
    - レート制限（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）、429 の Retry-After を尊重。
    - 401 発生時にリフレッシュトークンで自動的に id_token を更新して再試行（1 回のみ）。
    - ページネーション対応の fetch_* 関数（株価・財務・マーケットカレンダー）。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT による冪等保存。
    - データ整形ユーティリティ（_to_float / _to_int）を提供し、型変換の失敗を安全に扱う。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード収集・記事正規化の実装（URL 正規化、トラッキングパラメータ除去、テキスト前処理）。
    - 安全対策: defusedxml による XML パース、受信サイズ制限（最大 10MB）、HTTP(S) スキーム制限、SSRF 領域の考慮。
    - 挿入はバルクチャンク化とトランザクション化して効率化。
    - デフォルト RSS ソース (Yahoo Finance business) を提供。
- リサーチ（研究）モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR、平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を実装。
    - 過去データスキャン範囲や窓サイズを考慮した実装（営業日→カレンダー日バッファ）。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）と IC（Spearman ρ）計算、ファクター統計サマリー、順位関数(rank)を実装。
    - 外部依存を持たず純 Python / DuckDB のみで実装。
  - research パッケージのエクスポートを整備。
- 戦略（strategy）モジュール (src/kabusys/strategy)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research で計算した raw ファクターをマージし、ユニバースフィルタ（最低株価・20日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。DuckDB features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - ルックアヘッドバイアス回避の観点で target_date 時点のデータのみを使用。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合して複数コンポーネント（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
    - 重みの入力検証・正規化、デフォルト重みと閾値（BUY閾値=0.60）を実装。
    - Bear レジーム判定（AI の regime_score 平均が負であれば BUY を抑制、サンプル数不足時は判定しない）。
    - 保有ポジションのエグジット判定（ストップロス -8%／score 降下の2条件を実装）。SELL 優先ポリシーを採用（SELL がある銘柄は BUY から除外）。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
  - strategy パッケージのエクスポートを整備。
- 実行層 placeholder (src/kabusys/execution/__init__.py) を用意（将来の実装領域）。

Security
- RSS パースに defusedxml を採用し XML ベースの攻撃を軽減。
- ニュースの URL 正規化とトラッキングパラメータ除去で識別子一貫性を確保。
- .env 読み込み時に OS 環境変数を保護する機構（protected set）を導入。
- J-Quants クライアントでトークン再取得/リトライ処理を厳格化し、認可・ネットワークエラーへ堅牢に対応。

Performance & Reliability
- DuckDB を用いた集計・ウィンドウ処理で大規模データに対する高速処理を想定。
- DB 書き込みは executemany + トランザクション（BEGIN/COMMIT/ROLLBACK）で原子性・効率化を実現。
- J-Quants API 呼び出しは固定間隔スロットリング＋再試行でレート制限と一時障害を吸収。
- ニュースのバルク INSERT をチャンク化し SQL 長制限を回避。

Notable design decisions / Limitations
- ルックアヘッドバイアスの防止を方針として明文化（target_date 時点のデータのみを参照）。
- 一部のエグジット条件（トレーリングストップ／時間決済）は未実装（コードコメントで TODO と記載）。
- デフォルトで AI ニューススコアが未登録の場合は中立(0.5)で補完する設計。
- .env パーサは複雑な引用・エスケープ・インラインコメントに対応するが、稀なケースでの差異に注意が必要。
- execution 層（実際の発注）はまだ実装されていないため、本リリースは主にデータ取得・ファクター計算・シグナル生成の基盤提供を目的としている。

Acknowledgements / Notes
- 本 CHANGELOG は提供されたソースコードの実装内容から推測して作成しています。実際のリリースノート作成時には変更者（コミットログ）やリリース日、影響範囲の確認を推奨します。