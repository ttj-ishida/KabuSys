# CHANGELOG

すべての重要な変更点を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased: 未リリースの変更（現在は空）
- 各リリースには実装された機能・修正・注意点をカテゴリ別に記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。以下はコードベースから推測される主な追加・実装点です。

### Added
- パッケージ基礎
  - パッケージメタ情報: バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に追加。

- 設定管理
  - 環境変数・.env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env の行パーサを実装（コメント、export プレフィックス、クォート付き値、インラインコメントの扱いに対応）。
    - 上書き保護（protected）機構：既存 OS 環境変数を保護して .env.local による不注意な上書きを防止。
  - Settings クラスで型安全に各種設定を取得するプロパティを提供（J-Quants / kabu API / Slack / DB パス / env / log_level 等）。
    - env と log_level のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- データ取得・保存（J-Quants API）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）を実装。
    - 固定間隔のレートリミッタ（120 req/min）を導入。
    - リトライ戦略（最大 3 回、指数バックオフ、HTTP 408/429/5xx に対する再試行）。
    - 401 受信時のリフレッシュトークンを用いた id_token 自動更新（1 回だけ再試行）。
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（冪等性のため ON CONFLICT DO UPDATE を使用）。
    - 取得時刻の記録（fetched_at を UTC ISO 形式で保存）により Look-ahead バイアスの追跡を容易化。
    - 型変換ユーティリティ `_to_float`, `_to_int` を提供（変換失敗時の安全な None 返却）。

- ニュース収集
  - RSS ニュース収集モジュール（src/kabusys/data/news_collector.py）を実装。
    - RSS 取得・解析、記事正規化、トラッキングパラメータ除去、ID 生成（正規化 URL の SHA-256 部分）などを実装。
    - 安全対策: defusedxml を利用して XML 攻撃を防止、受信サイズ制限（MAX_RESPONSE_BYTES）、HTTP スキーム制限、SSRF 回避ロジックを考慮。
    - DB への冪等保存（ON CONFLICT / DO NOTHING 想定）とバルク挿入のチャンク化。
    - デフォルト RSS ソースを1件追加（Yahoo Finance ビジネスカテゴリ）。

- リサーチ / ファクター計算
  - Research モジュール群を実装（src/kabusys/research/*）。
    - ファクター計算（src/kabusys/research/factor_research.py）
      - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）。
      - ボラティリティ: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio。
      - バリュー: PER（price/EPS）、ROE（raw_financials からの最新財務データ結合）。
      - 各関数は DuckDB の prices_daily / raw_financials を参照し日付ウィンドウで計算。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の forward returns をまとめて取得。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（ties を平均ランクで処理）。
      - ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）。
    - zscore_normalize をデータユーティリティとして公開（src/kabusys/research/__init__.py 経由で data.stats を再エクスポート）。

- 戦略（Strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究用ファクターを統合して features テーブル向けに正規化・クリップ・UPSERT する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - Zスコア正規化適用（±3 でクリップ）、DuckDB トランザクション単位で日付の置換（冪等性確保）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア（final_score）を計算する generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算（シグモイド変換・逆転処理等）。
    - 重み指定を受け付け、デフォルト重みからのマージ・検証・リスケールを実装（不正な値は警告して無視）。
    - Bear レジーム判定（AI の regime_score に基づく市場判定）により BUY シグナル抑制を実装。
    - エグジット判定（ストップロス -8% / final_score の閾値割れ）を実装し SELL シグナルを生成。
    - signals テーブルへの日付単位置換（トランザクションで原子性保証）で冪等性を担保。
    - 保有ポジションの価格欠損時には SELL 判定をスキップする安全措置、features に無い保有銘柄は score=0 として扱う挙動を明記。

- ロギングとエラーハンドリング
  - 各処理で詳細ログ（info/warning/debug）を出力するよう実装。トランザクション失敗時の ROLLBACK と警告ログを含む。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Security
- RSS パーシングに defusedxml を使用、受信サイズ制限、URL のスキーム検証、トラッキングパラメータ除去などで外部入力に対する安全策を講じています。
- J-Quants クライアントはトークン自動リフレッシュとレート制御・リトライ制御を備え、API 利用時の誤動作や不正アクセスのリスクを低減。

### Performance
- DuckDB に対するバルク挿入（executemany）やウィンドウ関数を活用した集計でデータ処理の効率化を図っています。
- API レート制御は固定間隔のスロットリング実装で簡潔なレート制限維持を実現。

### Notes / Design decisions
- ルックアヘッドバイアス回避: 計算・シグナル生成は target_date 時点のデータのみ参照する設計。取得時刻（fetched_at）は UTC で保存。
- 冪等性: DB 書き込みは日付単位の置換（DELETE してから INSERT）で実現。J-Quants 保存は ON CONFLICT DO UPDATE を使用。
- 外部サービス（発注 API / execution 層）への依存は戦略層で持たない設計（戦略は signals テーブル生成までを担当）。
- 一部未実装の拡張（例: トレーリングストップ、時間決済、PBR・配当利回り等）はコード内に TODO/Notice が残されています。

---

作成者: コードベースの実装内容から推測して自動生成。実際の変更履歴やリリースノート作成時はコミット履歴や変更差分・設計ドキュメントを参照して補足・調整してください。