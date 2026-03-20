CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
このプロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
-------------

- なし（初回リリースは 0.1.0 を参照してください）

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初期リリース。以下の主要モジュール・機能を追加。
  - kabusys.config
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルート判定: .git または pyproject.toml を起点に探索（CWD 非依存）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 高度な .env 行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
    - _load_env_file による protected（既存 OS 環境変数）を保持する上書き制御。
    - Settings クラスを提供（プロパティ経由で J-Quants / kabu / Slack / DB パス / 環境 / ログレベル等を取得）。
    - 設定値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック、必須キー未設定時は ValueError）。

  - kabusys.data.jquants_client
    - J-Quants API クライアントを実装。
      - 固定間隔レート制限（120 req/min）を RateLimiter で制御。
      - リトライ戦略（指数バックオフ、最大リトライ回数 3、HTTP 408/429/5xx を対象）。
      - 401 発生時はリフレッシュトークンから ID トークンを再取得して1回リトライ（トークンキャッシュ共有）。
      - ページネーション対応の fetch_* 関数（株価日足、財務、マーケットカレンダー）。
      - DuckDB へ冪等保存する save_* 関数（raw_prices / raw_financials / market_calendar）を実装（ON CONFLICT DO UPDATE）。
      - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換ロジック）。
      - fetched_at を UTC ISO8601 で記録し、look-ahead バイアスのトレースを可能に。

  - kabusys.data.news_collector
    - RSS フィード収集モジュールを実装（デフォルトは Yahoo Finance のビジネス RSS）。
      - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリパラメータ整列）。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および SSRF/IP 検査などの基本的な安全対策を想定。
      - 記事 ID を正規化 URL の SHA-256 で生成して冪等性を確保。
      - raw_news へのバルク保存を想定（チャンク化、ON CONFLICT DO NOTHING / INSERT RETURNING を想定した設計）。
      - news_symbols 等との紐付けを想定した設計。

  - kabusys.research
    - 研究用ファクター計算・解析モジュールを実装。
      - factor_research.calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（営業日ベース、ウィンドウ不足時は None）。
      - factor_research.calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率の計算。
      - factor_research.calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出。
      - feature_exploration.calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（1クエリでまとめて取得）。
      - feature_exploration.calc_ic: スピアマンのランク相関による IC 計算（同順位は平均ランクで処理、サンプル数 < 3 は None）。
      - feature_exploration.factor_summary / rank: ファクターの統計要約とランク計算ユーティリティ。
      - zscore_normalize をデータユーティリティとして公開（kabusys.data.stats から利用）。

  - kabusys.strategy
    - 特徴量エンジニアリングとシグナル生成ルーチンを実装。
      - feature_engineering.build_features:
        - research モジュールから生ファクターを取得してマージ。
        - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
        - 数値ファクターを Z スコア正規化し ±3 でクリップ。
        - DuckDB の features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
      - signal_generator.generate_signals:
        - features と ai_scores を統合して各コンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
        - シグモイド変換・欠損補完（None は中立値 0.5）により final_score を算出。
        - デフォルト重みは StrategyModel.md の値（momentum 0.40 等）。ユーザ指定 weights は検証・正規化（未知キーや負値等は無視、合計が 1 にスケール）。
        - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数 >= 3 のとき）は BUY シグナルを抑制。
        - BUY は閾値（デフォルト 0.60）超の銘柄、SELL は保有ポジションに対するストップロス（-8%）またはスコア低下（threshold 未満）で生成。
        - positions の価格欠損処理や features に存在しない保有銘柄は final_score = 0 と見なす等の安全策を実装。
        - signals テーブルへ日付単位で置換（トランザクションにより原子性保護）。
      - いくつかの設計方針（ルックアヘッドバイアス防止、execution 層への依存排除、冪等性等）に従った実装。

  - その他
    - パッケージエントリポイント __init__ にバージョン情報を追加 (__version__ = "0.1.0")。
    - strategy と research の __all__ を適切に公開。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- news_collector で defusedxml を利用して XML の脆弱性（XML Bomb 等）に対処する設計を採用。
- news_collector に受信サイズ上限、URL 正規化、トラッキングパラメータ除去などの入力検証を導入。

Known limitations / Notes
- execution パッケージは存在するが実装ファイルは空（発注処理・API 統合は別途実装必要）。
- signal_generator の SELL 条件ではトレーリングストップ・時間決済など一部仕様は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の DB 保存部分は設計（チャンク化・冪等）を備えているが、外部 RSS の実行時挙動やネットワークの詳細な耐性検証は追加テストが必要。
- J-Quants クライアントは urllib を使用した同期実装。高スループット環境や非同期処理が必要な場合は別途改修を推奨。

Authors
- 初期実装者（コードベースから推測して CHANGELOG を作成）

--- 

脚注:
- 本 CHANGELOG は提示されたコードベースの内容から推測して作成しました。実際のリリースノートにはコミット履歴・イシュー・マイグレーション手順などを補足してください。