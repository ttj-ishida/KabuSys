Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

履歴
----

### [0.1.0] - 2026-03-21 (初回リリース)

Added
-----
- パッケージ全体の初期実装を追加。
  - パッケージ名: kabusys, バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を手がかりに自動探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーが複数の形式に対応:
    - export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 環境変数取得ユーティリティと検証:
    - 必須値チェック（_require）で未設定時に ValueError を送出。
    - settings クラスにプロパティとして以下を提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルトあり)
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH（Pathで返す）
      - KABUSYS_ENV（development, paper_trading, live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
      - is_live / is_paper / is_dev の便利プロパティ

- データ収集/保存 (src/kabusys/data)
  - J-Quants クライアント (jquants_client.py)
    - REST 呼び出しユーティリティを実装（_request）。
    - レート制限管理（120 req/min 固定間隔スロットリング）を実装（_RateLimiter）。
    - リトライ/指数バックオフロジック（408/429/5xx を対象、最大 3 回）。
    - 401 発生時の自動トークンリフレッシュ（1回のみリトライ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_ 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への冪等保存関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - ON CONFLICT DO UPDATE による重複排除、取得時刻 (fetched_at) の UTC 記録
    - 入力パースユーティリティ: _to_float / _to_int（不正値は None にフォールバック）
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得と記事正規化の基本実装。
    - デフォルト RSS ソース（例: Yahoo Finance のカテゴリ RSS）。
    - 記事ID を URL 正規化（トラッキングパラメータ除去）後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - 受信最大バイト数制限（10 MB）や SSRF/非 HTTP スキーム等の安全対策設計理念を導入。
    - バルク INSERT のチャンク化をサポート（パフォーマンス/SQL 長対策）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB の prices_daily を用いて計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true range の NULL 伝播制御あり）。
    - calc_value: raw_financials と prices_daily を結合して per / roe を計算（最新財務レコードを選択）。
    - 実装方針として DuckDB の SQL ウィンドウ関数中心で高速かつ正確に計算。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効サンプルが 3 未満なら None）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 平均ランク（同順位は平均）を返すユーティリティ（丸めによる ties 対応）。
  - research パッケージ __all__ を用意し、上記関数を公開。

- 戦略 (src/kabusys/strategy)
  - feature_engineering.py:
    - research 側で計算された生ファクターを取り込み、ユニバースフィルタ（最低株価/最低平均売買代金）適用、Zスコア正規化（kabusys.data.stats.zscore_normalize 呼び出し）、±3 クリップを実施。
    - features テーブルへ日付単位の置換（DELETE + バルク INSERT）による冪等書き込み。
  - signal_generator.py:
    - features と ai_scores を統合し、各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損値は中立値 0.5 で補完する仕様。
    - デフォルト重みと閾値を定義（例: momentum 0.40, threshold 0.60）。
    - Bear レジーム検出により BUY シグナル抑制（ai_scores の regime_score 平均が負かつサンプル数閾値あり）。
    - 保有ポジションのエグジット判定（ストップロス -8%、スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへの日付単位置換（トランザクションで原子性を保証）。
    - weights 引数の妥当性検査と正規化（ユーザ入力の検証・不正値無視・合計再スケール）。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Security
--------
- ニュース RSS の XML パースに defusedxml を使用して XML 関連攻撃を軽減。
- ニュースの URL 正規化でトラッキングパラメータを除去し、冪等性とプライバシー保護を強化。
- HTTP クライアントでのタイムアウト/受信サイズ制限や SSRF を考慮した設計方針を適用。
- J-Quants クライアントは 401 時にトークンを自動リフレッシュするが、無限再帰を防ぐため制御あり。

注意事項 / 既知の制限
-------------------
- DuckDB のスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）が前提になっています。正しいテーブル定義を用意してから使用してください。
- 一部戦略ロジック（トレーリングストップや時間決済など）は positions テーブルに peak_price / entry_date といった追加カラムがないため未実装です（TODO）。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境を準備することを推奨します。
- news_collector は外部 RSS の多様性に応じた追加正規化が必要になる場合があります（HTML/エンコードの扱い等）。

移行 / 利用時の注意
------------------
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - KABUSYS_ENV（オプション: development|paper_trading|live、デフォルト development）
  - LOG_LEVEL（オプション: DEBUG|INFO|...、デフォルト INFO）
  - DUCKDB_PATH / SQLITE_PATH（オプション）
- 自動 .env ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しではレート制限（120 req/min）とリトライポリシーが組み込まれています。大規模なデータ取り込み時は API 利用規約・レートに注意してください。

今後の作業候補（未実装 / 改善点）
-------------------------------
- positions に必要な履歴情報（peak_price, entry_date）を記録し、トレーリングストップ・時間決済を実装する。
- ニュースの本文処理（HTML タグ除去・言語処理）やシンボル抽出の強化。
- 単体テスト・統合テストの追加（特にネットワーク障害・ページネーション・DB トランザクション周り）。
- パフォーマンスの観点から DuckDB 用のインデックス/パーティショニング方針のドキュメント化。

お問い合わせ
------------
バグ報告・改善提案はリポジトリの Issue にお願いします。