CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。
通常の慣例に従い、バージョンごとに追加（Added）、変更（Changed）、修正（Fixed）、セキュリティ（Security）などのカテゴリで記載します。

[Unreleased]
------------

（現在なし）

[0.1.0] - 2026-03-20
-------------------

Added
- 初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能群を実装。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - 環境設定 / 設定管理
    - src/kabusys/config.py
      - .env および .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを提供（テスト向け）。
      - export 形式・コメント・クォート・エスケープに対応した .env パーサを実装（厳密なパースロジック）。
      - 必須変数取得で _require を用い ValueError を送出。settings オブジェクト経由のプロパティアクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など）。
      - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジックを実装（許容値を定義）。
  - データ取得 / 永続化（J-Quants）
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。株価日足・財務データ・マーケットカレンダー等の取得関数を提供（ページネーション対応）。
      - 固定間隔スロットリングによるレート制限（120 req/min）実装（_RateLimiter）。
      - 再試行（指数バックオフ、最大 3 回）とレスポンスコード（408/429/5xx）ハンドリング。
      - 401 Unauthorized 受信時にリフレッシュトークンでトークン再取得 → 1 回リトライする自動リフレッシュ機能。
      - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを共有。
      - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を用いた冪等性を確保。
      - 入力変換ユーティリティ（_to_float / _to_int）を実装し不正データを安全に扱う。
  - ニュース収集
    - src/kabusys/data/news_collector.py
      - RSS フィードから記事を収集して raw_news に保存する機能を実装（既定ソースに Yahoo Finance を含む）。
      - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
      - defusedxml を用いた XML の安全パース、受信サイズ制限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策、SSRF 緩和のためのスキームチェック等の堅牢化設計。
      - 記事 ID を正規化 URL の SHA-256 で生成し冪等性を担保。バルク INSERT チャンク処理を導入。
  - リサーチ（ファクター計算・探索）
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value 等の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
      - 各ファクターは date, code をキーとする dict リストで返す設計。欠損・データ不足時は None を返す挙動を明確化。
      - SQL ウィンドウ関数を活用して効率的に集計（MA200, ATR20, LAG 等）。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン（複数ホライズン）計算、IC（Spearman）計算、ファクター統計サマリーを提供。
      - pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装（軽量で移植性重視）。
    - src/kabusys/research/__init__.py にて主要関数をエクスポート。
  - 戦略層
    - src/kabusys/strategy/feature_engineering.py
      - 研究環境の生ファクターを正規化・合成して features テーブルへ保存する処理を実装（ユニバースフィルタ、Z スコア正規化、±3 クリップ、日付単位の置換：冪等）。
      - ユニバース定義（最低株価 300 円、20日平均売買代金 5 億円）を実装。
      - DuckDB 参照クエリで直近価格を取得し休場日対応を行う。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存（冪等）。
      - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算、シグモイド変換、重み付け（デフォルト重みを定義）を実装。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合）に基づく BUY 抑制ロジックを実装。
      - エグジット条件（ストップロス -8%、スコア低下）を実装。positions / prices_daily 参照で安全に SELL 判定を行う。
      - ユーザ重みのバリデーションと正規化（合計が 1.0 に再スケール）。
    - src/kabusys/strategy/__init__.py で主要 API を公開（build_features, generate_signals）。
  - その他
    - src/kabusys/execution パッケージの骨組みを準備（__init__.py が存在）。
    - ロギング出力・警告メッセージを多用し、運用時の診断性を向上。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュースパーサに defusedxml を利用し XML 脆弱性に対処。
- news_collector で受信サイズ制限や URL スキーム検証などの対策を盛り込み、外部入力による DoS / SSRF リスクを低減。

Notes / 設計上の注意
- ルックアヘッドバイアス対策を通底する設計方針として、各処理は target_date 時点で「システムが知り得るデータのみ」を参照するようになっています（feature_engineering / signal_generator / research）。
- DuckDB をデータ処理の一貫した基盤として利用しており、SQL ウィンドウ関数を多用してパフォーマンスを改善しています。
- 外部依存を最小化する設計（研究モジュールは pandas 等に依存しない）により軽量性とテスト容易性を確保。
- トークンの自動リフレッシュやレート制御、リトライ等、実運用を想定した堅牢な実装を行っていますが、本番環境での安全な運用には適切なモニタリングとエラー通知（例: Slack 連携）設定が推奨されます。
- 未実装 / 今後の拡張予定（ソースコード内注記）
  - signal_generator のトレーリングストップや時間決済（positions テーブルに peak_price / entry_date が必要）。
  - research 層の追加ファクター（PBR・配当利回りなど）。
  - execution 層と実際の発注ロジックの統合（現時点では発注 API への直接依存は持たない設計）。

署名
- この CHANGELOG は現行のコードベースから推測して作成しています。実際のリリースノートとして利用する場合は、追加の運用情報や変更理由、著者情報を併記することを推奨します。