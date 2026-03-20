Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトでは "Keep a Changelog" の形式に従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-20
-------------------

初回リリース。主に日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下はコードベースから推測できる主な追加点・設計上の特徴です。

Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名・バージョン定義（0.1.0）と公開モジュール一覧の設定。

- 環境変数・設定管理
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の行パーサを独自実装（export プレフィックス、クォート内エスケープ、インラインコメント処理対応）。
    - OS 環境変数保護（読み込み時の protected set）および override 挙動をサポート。
    - 必須環境変数検査を提供する _require() と Settings クラス（J-Quants / kabuAPI / Slack / DBパス / 環境・ログレベル検証）。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値のバリデーション）を実装。

- データ取得・保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアント実装（株価日足、財務データ、マーケットカレンダー取得）。
    - 固定間隔スロットリングによるレート制限制御（120 req/min を満たす RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429/5xx 対応）。429 の場合は Retry-After ヘッダ優先。
    - 401 エラー時のトークン自動リフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：
      - fetched_at を UTC ISO8601 形式で付与（Look-ahead バイアス追跡のため）。
      - ON CONFLICT DO UPDATE による冪等保存。
      - PK 欠損レコードをスキップし警告出力。
      - 型変換ユーティリティ（_to_float, _to_int）で安全に変換。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を収集し raw_news へ保存するための基盤。
    - デフォルト RSS ソース（Yahoo Finance）定義、受信サイズ制限（10MB）など保護策。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント削除）を実装。
    - 記事IDは正規化後の SHA-256 を利用する設計（冪等性確保）。
    - defusedxml を使った安全な XML パース、HTTP スキーム制限等のセキュリティ対策を考慮。
    - バルク INSERT のチャンク処理とトランザクション単位の DB 書き込み設計。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py:
    - モメンタム（1/3/6ヶ月リターン、MA200乖離）、ボラティリティ（20日 ATR・相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）などのファクター計算関数（calc_momentum, calc_volatility, calc_value）。
    - prices_daily / raw_financials テーブルの SQL ウィンドウ関数を多用した実装で、データ不足時は None を返す安全設計。
    - スキャン範囲にカレンダーバッファを取り、週末／祝日の欠損に対応。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応し一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関の算出（同順位は平均ランク処理）。
    - 統計サマリー（factor_summary）と rank ユーティリティ（浮動小数丸めで ties 対応）。
    - 外部ライブラリに依存しない実装方針。

  - src/kabusys/research/__init__.py: 上記関数群を公開。

- 戦略（Strategy）モジュール
  - src/kabusys/strategy/feature_engineering.py:
    - research モジュールが算出した生ファクターを統合して features テーブルへ保存する処理（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（外部 zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位での置換（DELETE + bulk INSERT）をトランザクションで行い冪等性・原子性を確保。
    - ルックアヘッドバイアス回避のため target_date 時点までのデータのみを参照。

  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores（AI ニューススコア、レジームスコア）を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成（generate_signals）。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（各種変換: シグモイド、反転等）。
    - weights の検証・マージ・再スケール処理（不正な値はログ警告でスキップ）。
    - AI レジームスコアの平均に基づく Bear 判定（サンプル数不足時は False）で BUY を抑制。
    - SELL 判定ロジック（stop loss: -8%／score drop）を実装。SELL は BUY より優先（BUY から除外しランク再付与）。
    - 日付単位での signals テーブル置換（トランザクション + bulk insert）で冪等性を確保。
    - 保有ポジション参照（positions テーブル）における価格欠損時の判定スキップとログ出力。

- モジュール結合
  - src/kabusys/strategy/__init__.py: build_features / generate_signals を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集で defusedxml を利用して XML 関連攻撃を緩和。
- RSS レスポンスサイズ制限（MAX_RESPONSE_BYTES）や URL 正規化により SSRF / DoS リスク低減を意識した設計。
- J-Quants クライアントでの認証トークン処理と自動リフレッシュにより資格情報エラーに対処。

Notes / 設計上の注意
- 多くの処理は DuckDB を前提とした SQL 実行と Python 側ロジックの組合せで実装されています。prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルスキーマが前提になります（スキーマ定義はコードベースに明示されていないため、導入時に合わせたテーブル作成が必要です）。
- Look-ahead バイアス回避のため、各計算は target_date 時点のデータだけを用いる設計になっています。
- J-Quants API 呼び出しはレート制限と再試行の実装があるものの、実行環境やネットワーク条件によっては追加の監視やカスタマイズが必要です。
- NewsCollector の一部（URL 検査やレコード挿入の細部など）はファイル末端で続きの実装を想定している箇所が見られます。実運用前に全コードパスのレビュー・テストを推奨します。

Backward compatibility / Migration
- 初回リリースのため互換性問題はありません。

Acknowledgements
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートや利用上の正確な注意はリポジトリのドキュメントや開発者による公式アナウンスを参照してください。