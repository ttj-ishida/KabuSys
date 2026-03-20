CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
なお、この変更履歴は与えられたコードベースから推測して作成しています（実装コメントや docstring に基づく要約）。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-20
-------------------

Added
- 基本パッケージ初期リリース:
  - パッケージ名: kabusys、バージョン 0.1.0
  - エントリポイント (src/kabusys/__init__.py) でサブモジュールを公開: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (src/kabusys/config.py):
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）
  - .env の細かいパース処理を実装（コメント行、export プレフィックス、クォート内のエスケープ、インラインコメント処理等に対応）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルの検証等）
  - 必須環境変数チェック（_require）で未設定時は ValueError を送出

- データ取得クライアント (src/kabusys/data/jquants_client.py):
  - J-Quants API クライアントを実装
  - レート制限対応（固定間隔スロットリング、120 req/min）
  - 再試行（指数バックオフ、最大3回、408/429/5xx 対応）、429 の Retry-After 優先
  - 401 受信時のリフレッシュトークン自動更新（1回まで）とトークンキャッシュ
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
    - INSERT ... ON CONFLICT DO UPDATE を用い重複を排除
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡）
    - PK 欠損行はスキップし警告ログを出力
  - 型変換ユーティリティ (_to_float / _to_int) を備え、入力の不正値を安全に扱う

- ニュース収集 (src/kabusys/data/news_collector.py):
  - RSS フィード取得・記事抽出処理 (デフォルトで Yahoo Finance のビジネス RSS を登録)
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）
  - defusedxml を使った XML パース（XML Bomb 等の攻撃防御）
  - 受信サイズ制限（MAX_RESPONSE_BYTES）や SSRF に配慮した URL 検証方針（HTTP/HTTPS のみ受け入れ等が想定）
  - raw_news への冪等保存（ON CONFLICT DO NOTHING、バルク挿入チャンク化）および記事ID を SHA-256 ハッシュで一意化

- 研究用ファクター計算 (src/kabusys/research/factor_research.py):
  - モメンタムファクター calc_momentum（1m/3m/6m リターン、MA200 乖離）
  - ボラティリティ/流動性ファクター calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
  - バリューファクター calc_value（最新の raw_financials を参照して PER / ROE を算出）
  - DuckDB に対する効率的な SQL 実装（ウィンドウ関数、範囲制限、NULL 伝播制御など）
  - データ不足時は None を返す設計（堅牢性を確保）

- 研究支援ユーティリティ (src/kabusys/research/feature_exploration.py):
  - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日がデフォルト）
  - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、結合・欠損除外・最小サンプル判定）
  - ランク変換ユーティリティ rank（同順位は平均ランク）
  - factor_summary（count, mean, std, min, max, median を計算）
  - 標準ライブラリのみでの実装（pandas 等に依存しない）

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py):
  - research の生ファクターを取得し正規化・合成して features テーブルに保存する build_features を実装
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
  - Z スコア正規化（kabusys.data.stats.zscore_normalize の利用）および ±3 でクリップ
  - 日付単位の置換（DELETE + INSERT）で冪等的かつトランザクションによる原子性を保証
  - 価格取得は target_date 以前の最新価格を参照して休日・欠損に対応

- シグナル生成 (src/kabusys/strategy/signal_generator.py):
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成する generate_signals を実装
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を個別に算出
  - シグモイド変換・欠損補完（None を中立 0.5 で補完）により偏りを抑制
  - weights の入力検証と正規化（未知キーや不正値は無視、合計再スケール）
  - Bear レジーム判定（ai_scores の regime_score 平均が負で一定サンプル数以上で判定）による BUY 抑制
  - エグジット（SELL）判定ロジックを実装（ストップロス -8% とスコア閾値割れ）
    - 注記: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入）
  - features が空の場合は BUY シグナルを生成せず SELL 判定のみ実施

- パッケージ公開 (src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py)
  - 主要 API の再エクスポート（build_features, generate_signals, calc_* 等）

Security
- XML パースで defusedxml を採用（news_collector）
- ニュース URL の正規化・トラッキングパラメータ除去・HTTP/HTTPS 制限など SSRF/追跡防止に配慮
- J-Quants クライアントは認証トークンの取り扱いと自動リフレッシュの制御を実装（無限再帰を避けるための allow_refresh フラグ）

Known issues / Notes
- execution パッケージは空の状態（実際の発注実装は未提供）
- 一部エグジット条件（トレーリングストップ、時間決済）は未実装で将来の拡張が必要
- DB スキーマ（テーブル名/カラム）はコード側の期待に依存するため、利用前に DuckDB スキーマを準備する必要あり（使用テーブル例: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, news_symbols）
- settings が必須とする環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
- research モジュールは外部解析ライブラリに依存せず標準ライブラリのみで実装されているため、大規模データ操作での性能チューニングは今後の課題

Acknowledgments
- この CHANGELOG は提供されたソースコードのコメント・実装内容から推測して作成しています。実際の変更履歴やリリースノートは、開発履歴（コミットログ等）に基づいて補完してください。