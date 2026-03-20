Keep a Changelog に準拠した CHANGELOG.md（日本語）をコードベースから推測して作成しました。

保持方針の簡単な説明:
- フォーマットは Keep a Changelog に準拠しています。
- 日付は本ファイル生成日（2026-03-20）を初期リリース日として記載しています。
- 記載内容は提供されたソースコードから推測した機能追加・設計意図・重要実装ポイントです。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマットについては Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-20
--------------------
Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
- パッケージ構成:
  - kabusys.config
    - .env または環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出 (.git または pyproject.toml) により CWD に依存しない自動ロードを実現。
    - .env / .env.local の読み込み順序と override/protected（OS 環境変数保護）をサポート。
    - .env 行パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境モード/ログレベル検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - kabusys.research
    - factor_research: calc_momentum / calc_volatility / calc_value を実装。
      - prices_daily / raw_financials を DuckDB 経由で参照。
      - モメンタム（1M/3M/6M・MA200乖離）、ATR/相対ATR、平均出来高/売買代金、PER/ROE 等を計算。
      - 窓サイズやスキャンバッファを定義し週末・祝日欠損に対応。
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装。
      - 複数ホライズン（デフォルト: 1,5,21）で将来リターンを計算。
      - Spearman（ランク相関）による IC 計算、基本統計量のサマリーを返す。
      - 外部依存（pandas 等）を持たず、標準ライブラリと DuckDB のみで実装。
  - kabusys.strategy
    - feature_engineering.build_features を実装。
      - research の生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位の置換（冪等）で保存。
      - DuckDB トランザクションを使い原子性を保つ。
    - signal_generator.generate_signals を実装。
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
      - デフォルト重みと閾値（デフォルト閾値 0.60）を持ち、ユーザ指定の weights を検証してスケーリング。
      - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
      - 保有ポジションに対するエグジット判定（ストップロス -8% など）を実装し SELL シグナルを生成。
      - BUY / SELL を signals テーブルへ日付単位の置換（冪等）で保存。SELL 優先ポリシーを採用（SELL 対象は BUY から除外）。
  - kabusys.data
    - jquants_client: J-Quants API クライアントを実装。
      - rate limiter（120 req/min 固定間隔スロットリング）を実装。
      - リトライ（指数バックオフ、最大 3 回）、特定ステータス(408/429/5xx) の再試行対応。
      - 401 受信時にリフレッシュトークンで自動的に ID トークンを更新して再試行（無限再帰防止）。
      - fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）でページネーション対応。
      - save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）で DuckDB に対して ON CONFLICT を用いた冪等保存を提供。
      - データの fetched_at は UTC で記録し、Look-ahead バイアスのトレースを可能にする。
      - 型変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う。
    - news_collector: RSS ニュース収集モジュールを実装。
      - defusedxml を用いて XML 関連の脅威を軽減。
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）を実装。
      - 最大受信サイズ制限（10MB）、HTTP スキーム検証、SSRF 緩和の設計考慮。
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
      - バルク INSERT のチャンク化、INSERT RETURNING による正確な挿入件数取得方針（実装の指針）。
  - kabusys.execution
    - パッケージプレースホルダを追加（実装は空の __init__）。

Other notable implementation details
- ルックアヘッドバイアス対策: research/strategy 層は target_date 時点のデータのみを参照する設計。
- 冪等性: DuckDB へのデータ書き込みは可能な限り ON CONFLICT / 日付単位の DELETE→INSERT による置換で実装し、再実行が安全に行える。
- エラーハンドリングとログ: 各所で警告/ログを出力し、トランザクションの ROLLBACK フォールバックやリトライ状況を記録。
- 依存: 実行時は DuckDB と defusedxml を使用。外部の重いデータ処理ライブラリに依存しない方針。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- news_collector で defusedxml を使用し XML 攻撃対策を講じています。
- jquants_client はトークンやネットワークエラー時の安全なリトライ・トークン更新を実装。

Notes / 今後の実装候補（コード内コメントより）
- signal_generator のトレーリングストップや時間決済（positions に peak_price / entry_date が必要）等、追加のエグジット条件が未実装。
- news_collector の実際の INSERT RETURNING 実装や RSS フィード拡張は設計指針レベルで記載されている箇所がある（実装の拡張余地あり）。
- さらなるテストや運用時の観測（monitoring）/ execution 層の実装が予定される模様。

---

補足:
- ここに記載した CHANGELOG はソースコードに記載された関数名・ファイル・コメントから推測して作成しています。実際のリリースノートとして公開する場合は、実装済みのテスト結果やバージョン管理履歴に基づいて調整してください。