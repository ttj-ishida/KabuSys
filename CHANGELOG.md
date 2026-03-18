# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

なお、以下は提供されたコードベースの内容から推測して作成した変更履歴です。

------------------------------------------------------------
Unreleased
------------------------------------------------------------
- 予定/検討中
  - strategy/execution パッケージの具象実装（発注ロジック・ポジション管理・バックテスト）の追加
  - 追加ファクター（PBR・配当利回り等）の実装
  - 単体テスト・CI（DuckDB を使った統合テスト）の整備
  - 既存モジュールの性能改善（DuckDB クエリ最適化、RSS フェッチの並列化等）
  - ドキュメント整備（API 使用例、運用手順、DB スキーマ図）

------------------------------------------------------------
[0.1.0] - 2026-03-18
------------------------------------------------------------
Added
- 基本パッケージ構成を追加
  - kabusys パッケージを初期化（__version__ = 0.1.0、主要サブパッケージを __all__ に定義）
  - 空のサブパッケージプレースホルダ: execution/, strategy/

- 環境設定管理（kabusys.config）
  - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から判定）
  - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）、.env.local は既存環境変数を上書き可能
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱いの改善
  - Settings クラスを提供（必須環境変数取得ヘルパと各種検証）
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト（DUCKDB_PATH / SQLITE_PATH）
    - KABUSYS_ENV 値検証（development / paper_trading / live）
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパ

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - 日足（daily quotes）、財務データ（statements）、マーケットカレンダー取得関数を実装
    - ページネーション対応
    - レート制限対応（120 req/min 固定間隔スロットリング）
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）
    - 401 受信時にリフレッシュトークンで自動更新して1回リトライ
    - fetched_at を UTC で記録（look-ahead bias 対策）
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装、冪等性を確保するため ON CONFLICT を使用
    - 値変換ユーティリティ (_to_float / _to_int) の実装

  - ニュース収集モジュール（data/news_collector.py）
    - RSS フィード取得（fetch_rss）と記事保存（save_raw_news）を実装
    - セキュリティ対策：
      - defusedxml を用いた XML パース（XML Bomb 対策）
      - HTTP リダイレクト時にスキームとホストを検査して SSRF を防止（カスタム RedirectHandler）
      - ホストのプライベートアドレス判定（DNS 解決した全 A/AAAA を検査）
      - URL スキームの検証（http/https のみ許可）
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後の検査（Gzip bomb 対策）
      - トラッキングパラメータ（utm_* 等）を除去して URL 正規化、SHA-256 を使った記事 ID 生成（32 文字ハッシュ）
    - raw_news へのバルク挿入はチャンク化してトランザクション内で処理、INSERT ... RETURNING で挿入済み ID を正確に取得
    - 記事と銘柄コードの紐付け機構（news_symbols 保存用関数と抽出ロジック）
    - 銘柄コード抽出（4桁数字パターン）と既知コードフィルタリングの実装
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを追加

  - DuckDB スキーマ定義（data/schema.py）
    - Raw Layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等）
    - 初期化・DDL をコードで管理する基盤を整備

- リサーチ / 特徴量（kabusys.research）
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得）
    - ランク相関（Spearman）による IC 計算 calc_ic（ランク関数を内部実装）
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）
    - 細かい数値検査（有限値のみを扱う等）
  - factor_research.py
    - Momentum, Volatility, Value ファクター計算関数を実装
      - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev（200日 SMA 乖離率、200 行未満は None）
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（ウィンドウ内のデータ不足は None）
      - calc_value: raw_financials と prices_daily を用いた PER / ROE（最新財務レコードを取得）
    - DuckDB を直接参照する設計（prices_daily / raw_financials のみを参照）
  - research パッケージの公開 API を整理（__all__）

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- ニュース収集での SSRF/XXE/DoS 対策を実装（defusedxml、リダイレクト検査、プライベートIP検出、受信サイズ制限など）
- J-Quants クライアントの認証リフレッシュおよび安全な再試行フローを実装（401 ハンドリング、Retry-After 尊重）

Notes / 運用上の注意
- 必須環境変数を設定しないと Settings が ValueError を投げます。通常はルート配下の .env を用意してください（.env.example を参照）。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、パッケージ配布後やテスト時に不要な読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限・再試行ポリシーを実装していますが、実運用では API 仕様や利用量に応じた調整が必要です。
- DuckDB への INSERT は ON CONFLICT 句を使用しているため冪等性が考慮されています。ただしスキーマやインデックスの変更時は注意してください。

------------------------------------------------------------
今後の改善候補（抜粋）
- strategy / execution の具現化（バックテスト・ライブ発注）
- データ取得ジョブのスケジューリングと状態管理（増分取得・フェッチメタデータ）
- ニュースの自然言語処理（キーワード抽出・類似記事クラスタリング）
- ロギング・メトリクスの標準化（Prometheus/Structured logging）
- 消費メモリ/IO の監視とパフォーマンスチューニング

------------------------------------------------------------

（この CHANGELOG はコードベースの現状から推測して作成しています。実際の変更履歴やリリースノートとは差異がある可能性があります。）