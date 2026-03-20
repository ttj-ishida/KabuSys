CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

[Unreleased]
-------------

(現在の公開バージョンは 0.1.0 のため未リリース項目はありません)

0.1.0 - 2026-03-20
------------------

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。

Added
- パッケージ初期版を追加
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開インターフェース: data, strategy, execution, monitoring を __all__ としてエクスポート

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数読み込み機能を実装
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索 (_find_project_root)
  - .env パーサ: export 構文・クォート・インラインコメント対応の堅牢なパーサ実装 (_parse_env_line)
  - 自動ロード順序: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数チェックと型・値検証を行う Settings クラス（J-Quants / kabu / Slack / DB 等の設定プロパティを提供）
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許可値集合）

- データ収集・保存 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - API 呼び出しの共通処理、ページネーション対応、JSON パース
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装
    - 再試行/指数バックオフ: 最大 3 回、408/429/5xx を対象にリトライ、429 の場合は Retry-After を優先
    - 401 時はトークン自動リフレッシュを 1 回実行してリトライ（無限再帰防止）
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を保つ ON CONFLICT DO UPDATE を使用
    - 型変換ユーティリティ _to_float / _to_int を提供（不正値・空値を None に変換）
    - fetched_at を UTC ISO8601 で保存し、Look-ahead バイアスのトレースが可能

  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得→前処理→raw_news への冪等保存ワークフローを実装
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID を SHA-256 で生成して冪等性確保
    - defusedxml を用いた XML パースで XML-Bomb 等の対策
    - HTTP/HTTPS のみ許可、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を軽減
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）および ON CONFLICT DO NOTHING による重複排除
    - デフォルト RSS ソース: Yahoo Finance（DEFAULT_RSS_SOURCES）

- リサーチツール群 (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum, Volatility, Value（PER/ROE）等を DuckDB の prices_daily/raw_financials を参照して計算
    - 各関数は (date, code) をキーとする dict リストを返す設計
    - ウィンドウ長・スキャン範囲（200 日 MA、ATR20 等）や欠損ハンドリングを明示
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns): デフォルトホライズン [1,5,21]、ホライズン検証
    - IC（Information Coefficient）計算 (calc_ic): スピアマンのρをランク計算で実装、サンプル数不足時は None を返す
    - factor_summary / rank ユーティリティを提供
    - Pandas 等の外部ライブラリに依存せず標準ライブラリ + DuckDB で実装（研究用途向け）

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research で得た生ファクターを統合・正規化して features テーブルへ UPSERT
  - ユニバースフィルタ実装: 最低株価 300 円、20 日平均売買代金 5 億円を下限とするフィルタ
  - Z スコア正規化 + ±3 でクリップ（外れ値耐性）
  - 日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を確保

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア (final_score) を計算、signals テーブルへ保存
  - デフォルト重み・閾値: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10、BUY 閾値 0.60
  - ストップロス判定（終値対平均約定価格 -8% 以下で SELL）
  - Bear レジーム検出: ai_scores の regime_score の平均が負（最低サンプル 3 件）で BUY を抑制
  - 欠損コンポーネントは中立 0.5 で補完して不当な降格を防止
  - SELL 優先ポリシー（SELL 対象は BUY から除外）、トランザクション + bulk INSERT による日付単位置換で冪等性確保
  - weights 引数でユーザ定義の重みを受け付け、検証・正規化を行う（無効値はスキップ）

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Security
- ニュース収集で defusedxml を利用して XML パースの安全性を確保
- ニュース収集で受信サイズ上限とスキーム検証により SSRF / DoS リスクを低減
- J-Quants クライアントでトークン更新処理の無限再帰防止とリトライ制御を実装

Known limitations / TODOs
- execution 層はパッケージ構成に含まれるが、実装ファイルは未提供（発注 API 連携は別実装予定）
- monitoring モジュールは __all__ に含まれているが詳細実装は未提供
- signal_generator 内で未実装のエグジット条件:
  - トレーリングストップ（ピーク価格追跡）および時間決済（保有 60 営業日超）のためには positions テーブルに peak_price / entry_date が必要
- news_collector の既定 RSS ソースは限定的（拡張が必要）
- research モジュールは外部集計・可視化ツールとの連携を想定しているが、Pandas 等の依存は意図的に排除

開発上の注意
- 多くの処理が DuckDB 接続を直接受け取る設計（テストしやすく、外部 API への直接アクセスを避ける）
- 冪等性とログ出力を重視（INSERT の ON CONFLICT、fetched_at/created_at の保存、警告ログ）

作者・貢献
- 初期実装: コードベースに同梱のモジュール群に基づく

ライセンス等のメタ情報はリポジトリの該当ファイルを参照してください。