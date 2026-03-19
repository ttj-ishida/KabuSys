CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
日付はコードベースから推測して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初回リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ で data / strategy / execution / monitoring を公開。

- 環境設定管理
  - 環境変数読み込みモジュールを追加（kabusys.config）。
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を自動ロードする仕組みを実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサを堅牢化：
    - export プレフィックス対応
    - シングル／ダブルクォートのエスケープ対応
    - 行内コメントやトラッキングコメントの扱いの改善
  - Settings クラスを提供し、必須キー取得時の検証（未設定は ValueError）や env/log_level の正当性チェックを実装。
  - デフォルト設定（KABUSYS_API_BASE_URL、データベースパス等）を提供。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを追加（kabusys.data.jquants_client）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を考慮）。
  - 401 レスポンス時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライする仕組みを実装（トークンキャッシュをモジュールレベルで保持）。
  - ページネーション対応（pagination_key）およびページ間でのトークン共有対応。
  - DuckDB への冪等保存ユーティリティを実装：
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE による upsert 挙動。
    - 生データ取り込み時の型変換ユーティリティ（_to_float / _to_int）。
    - PK 欠損行のスキップとログ出力。

- ニュース収集
  - RSS ニュース収集モジュールを追加（kabusys.data.news_collector）。
  - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を担保する方針を明記。
  - defusedxml を用いた XML パースで安全性を確保（XML Bomb 等の対策）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）や HTTP スキーム制限等の安全対策を導入。
  - トラッキングパラメータ（utm_* 等）の除去、クエリソート、フラグメント除去など URL 正規化処理を実装。
  - bulk insert のチャンク化や DB トランザクションで効率化・原子性を担保。

- 研究用 / ファクター計算
  - factor_research モジュールを実装（kabusys.research.factor_research）。
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - Value（PER / ROE：raw_financials から最新レコードを参照）
    - 欠損やデータ不足時の None 設定、営業日ベースの窓処理、スキャン範囲のバッファを考慮
  - feature_exploration を実装（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、営業日ベース、SQL で一括取得）
    - IC（Spearman ランク相関）計算（ties を平均ランクで扱う）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - ランク関数（ランク付けの平均ランク処理）を提供
  - research パッケージとして公開 API を __all__ にて整理。

- 特徴量エンジニアリング / シグナル生成（戦略）
  - feature_engineering.build_features を実装（kabusys.strategy.feature_engineering）。
    - research モジュール算出の生ファクターを統合し、ユニバースフィルタ（最小株価・最小売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - DuckDB の features テーブルへ日付単位で置換（DELETE→INSERT）する冪等処理。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照する設計。
  - signal_generator.generate_signals を実装（kabusys.strategy.signal_generator）。
    - features と ai_scores を統合して複合スコア（momentum / value / volatility / liquidity / news）を算出。
    - コンポーネントの数値変換（Zスコア→シグモイドなど）、欠損コンポーネントは中立 0.5 で補完。
    - 重みのマージ・正規化処理（デフォルト重みを定義、ユーザー指定値の検証と再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル閾値以上で判定）により BUY を抑制。
    - BUY（threshold ベース）と SELL（ストップロス / スコア低下）シグナルを生成し、signals テーブルへ日付単位の置換で保存。
    - SELL は BUY より優先して排除、ランク再付与などのポリシーを実装。
    - 一部エグジット条件（トレーリングストップ、時間決済）は未実装で注記あり。

- ロギング / エラーハンドリング
  - 主要処理での情報・警告ログを充実させ、DB トランザクション失敗時の ROLLBACK 失敗を警告ログに出力。
  - 外部 API のレスポンス異常や変換エラー時に詳細なエラーメッセージを出力。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パースに defusedxml を採用し XML 関連攻撃を軽減。
- ニュース収集で受信最大バイト数を設ける等、メモリ DoS 対策を実装。
- RSS の URL 正規化でトラッキングパラメータを除去、SSRF リスク軽減の注記。

Known issues / Limitations
- positions テーブルに peak_price / entry_date 等が無い想定のため、トレーリングストップや時間決済のエグジット条件は未実装（注釈あり）。
- 外部依存を極力排した設計（pandas 等不使用）だが、複雑な集計でパフォーマンスチューニングの余地あり。
- NewsCollector の実装は設計が含まれるが、実際の HTTP フェッチ・DB 保存ループの詳細実装は一部ファイル切れにより省略または続きが必要（コードベースからの推測による注記）。

開発者向けメモ
- 環境変数と .env の自動ロードはパッケージ配布後も機能するよう __file__ からプロジェクトルートを探索する設計。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨。
- DuckDB 接続を受け取る設計のため、単体テストではインメモリ DuckDB 接続を使って各関数を検証可能。

（以上）