# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

全体の概要（コードからの推測）
- 本リポジトリは日本株向けの自動売買システム「KabuSys」の初期実装です。
- 主な機能はデータ収集（J-Quants、RSS）、ファクター計算・特徴量作成、シグナル生成、設定管理、研究用ユーティリティです。
- DuckDB をデータストアに想定し、冪等性・トランザクション制御・エラー耐性に配慮した実装がなされています。

Unreleased
- （今のところなし）

0.1.0 - 2026-03-20
- Added
  - パッケージとエントリポイント
    - パッケージ初期化: kabusys.__version__ = "0.1.0"。主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。
  - 環境設定/ローディング（src/kabusys/config.py）
    - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルートの自動検出（.git または pyproject.toml）を行い、CWD に依存しない読み込みを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - 高機能な .env パース実装（コメント・export プレフィックス・シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いなど）。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス等の必須/既定値をプロパティ経由で取得。env / log_level の妥当性チェックや is_live / is_paper / is_dev の便宜プロパティを実装。
  - データ収集（src/kabusys/data/jquants_client.py）
    - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（株価・財務データ・マーケットカレンダー）を提供。
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を導入。
    - リトライロジック（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュを実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
    - 型変換ユーティリティ (_to_float / _to_int) を提供し、外部データの取り扱いを堅牢化。
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード収集の基礎実装を追加。デフォルトソース（Yahoo Finance）を定義。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去、小文字化）および記事ID の SHA-256 ハッシュ化による冪等性設計。
    - defusedxml を用いた XML パース（XML Bomb 対策）や受信サイズ制限（10MB）などのセキュリティ対策を採用。
    - SSRF 対策やチャンク化されたバルク INSERT による効率的な DB 保存方針を採用。
  - 研究用ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum / Volatility / Value 系ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を多用した SQL ベースの計算（MA200、ATR20、出来高平均、各種ラグの取得等）。
    - データ不足時の None ハンドリング、スキャンレンジのバッファ設計など実運用を見据えた設計。
  - 研究ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - rank は同順位を平均ランクで扱い、丸め誤差対策に round(..., 12) を採用。
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究モジュールから得た raw factors をマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを zscore_normalize（kabusys.data.stats から提供）で正規化し ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性を保証。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合してファクター別スコア（momentum/value/volatility/liquidity/news）を算出。最終スコア final_score を重み付き合算で計算。
    - デフォルト重み・閾値を定義。外部からの weights は検証・正規化して合計が 1.0 になるよう再スケール。
    - Bear レジーム判定（AI の regime_score 平均が負かつ十分なサンプル数）による BUY 抑制。
    - SELL 判定ロジック実装（ストップロス -8% 優先、スコア低下によるエグジット）。保有銘柄の価格欠損・features 未登録に対する警告ログあり。
    - signals テーブルへの日付単位置換をトランザクションで行い冪等性を確保。
  - パッケージ再エクスポート（src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py）
    - 主要 API を __all__ で公開（研究・戦略 API の簡易インポートを提供）。
  - その他
    - DuckDB を前提とした SQL 実行パターン（bulk insert、ROW_NUMBER による latest_fin 抽出 等）を採用。
    - ロギングを多用し、重要な箇所で情報・警告・デバッグを出力。

- Changed
  - （初期リリースのため該当なし）

- Fixed
  - （初期リリースのため該当なし）

- Security
  - RSS パースに defusedxml を利用して XML 攻撃を軽減。
  - ニュース URL 正規化とスキーム検査により SSRF リスクを軽減する方針を導入（実装の一部を確認）。
  - J-Quants クライアントは認証トークン取り扱いで自動リフレッシュを導入し、不正な再帰を防ぐフラグ（allow_refresh）を使用。
  - 外部入力値（weights, API レスポンス 等）に対する厳密な検証を実施（NaN/Inf/負値/型チェック）。

- Performance
  - API 呼び出しのレート制御（固定間隔）とリトライで安定性を向上。
  - DB 操作はバルク実行 / チャンク化 / トランザクションで最適化。
  - DuckDB 側のウィンドウ集計を活用し Python 側でのループを最小化。

- Reliability / Robustness
  - 多くの保存処理で ON CONFLICT / DO UPDATE による冪等性を実現。
  - features / signals の更新は日付単位で削除→挿入（トランザクション）し原子性を保証。
  - ネットワーク障害・HTTP エラーに対する堅牢なリトライロジックを実装。
  - データ欠損時の挙動（価格欠損での SELL 判定スキップ、features 欠損時の中立補完など）を明示。

- Breaking Changes
  - なし（初期リリース）

参考（実装上の注意点／未実装・今後の課題と推測）
- execution パッケージは存在するが実装ファイルは見当たらない（将来的に発注ロジックを想定）。
- signal_generator の SELL 条件でトレーリングストップや時間決済は未実装（コメントあり）。positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の完全な実装（RSS ダウンロード・パース・DB 挿入呼び出しの詳細）はこのスニペットでは途中まで。外部 URL/ネットワークの検査ロジックや実際の DB 保存ルーチンの完成が必要。
- 単体テスト / エンドツーエンドテストの存在は不明。環境変数の自動ロードはテストの都合で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）としているため、テスト導入はしやすい設計。

以上。コードを参照して推測した変更点・機能一覧です。追加で各モジュールごとの詳細な変更ログ（関数単位の履歴）やリリースノート文言の調整が必要であればお知らせください。