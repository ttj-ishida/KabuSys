CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-19
------------------

Added
- 初回リリースを追加（kabusys 0.1.0）。
- パッケージ構成
  - パッケージエントリポイント: src/kabusys/__init__.py（バージョン: 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring（execution は空の初期モジュール）。
- 環境設定 / ロード
  - src/kabusys/config.py: 環境変数管理を導入。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - OS 環境変数を保護する動作（.env の上書き制御、.env.local は上書き可）。
    - .env のパース機構を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの取り扱い等）。
    - 必須 env の取得時に _require() が未設定なら ValueError を送出。
    - 設定オブジェクト settings を提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル検証 API を提供。
- Data: J-Quants クライアント
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装（token 取得、日足・財務・マーケットカレンダー取得）。
    - レート制限管理（_RateLimiter、120 req/min 固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回再試行（再帰防止フラグあり）。
    - ページネーション対応（pagination_key を利用）。
    - DuckDB へ保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）。
      - 保存は冪等化（ON CONFLICT DO UPDATE）して重複や再取得に耐える実装。
      - fetched_at を UTC ISO 形式で記録して取得時刻をトレース可能に。
    - 型変換ユーティリティ（_to_float / _to_int）で不正値を安全に None に変換。
    - モジュールレベルの ID トークンキャッシュを導入（ページ間で共有、強制リフレッシュ可）。
- Data: ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィード収集モジュールを実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - XML パースの安全化に defusedxml を使用（XML Bomb 等の防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と SSRF に配慮した URL/スキームチェックの方針（ドキュメントに記載）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭を使う方針（冪等性確保）。
    - DB へのバルク挿入はチャンク化して実行（チャンクサイズ定義あり）。
    - SQL トランザクションでまとめて保存する設計（INSERT RETURNING による挿入数の精密取得を想定）。
- Research（研究用ユーティリティ）
  - src/kabusys/research/factor_research.py:
    - モメンタム / ボラティリティ / バリュー系ファクター計算を実装。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日データ不足時は None）。
    - calc_volatility: ATR（20日平均）、atr_pct、avg_turnover、volume_ratio（必要行数チェックあり）。
    - calc_value: target_date 以前の最新 raw_financials と当日の株価を用いて PER / ROE を算出（EPS 0 または欠損は None）。
    - SQL + DuckDB ウィンドウ関数を活用した効率的な実装。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、引数検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのρ、サンプル不足時は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）や基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで提供。
  - research パッケージの __all__ で主要関数群を公開。
- Strategy（戦略）
  - src/kabusys/strategy/feature_engineering.py:
    - 研究環境で算出した生ファクターを正規化・合成し features テーブルへ保存する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を実装。
    - 正規化は zscore_normalize（kabusys.data.stats 由来）を利用し ±3 でクリップ。
    - features テーブルへの日付単位置換（DELETE -> INSERT のトランザクション）により冪等化。
  - src/kabusys/strategy/signal_generator.py:
    - 正規化済み features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（news は AI スコアのシグモイド変換）。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）を実装。ユーザ指定重みは検証・正規化される。
    - Bear レジーム判定: ai_scores の regime_score 平均が負であり、かつサンプル数 >= 3 の場合に BUY を抑制。
    - エグジット判定（SELL）実装:
      - ストップロス（終値 / avg_price - 1 < -8%）。
      - final_score が閾値未満（score_drop）。
      - price 欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等化。SELL 優先のポリシーで BUY から除外しランクを再付与。
- logging / エラーハンドリング
  - 各所で詳細な logger 呼び出しを追加（info/warning/debug）して動作・異常条件をトレース可能に。
  - トランザクションでの ROLLBACK 失敗を警告ログ出力する耐障害性向上。
- ドキュメント的注記（コード内 docstring）
  - 多数のモジュールで設計方針・呼び出し制約（DuckDB のみ参照、発注 API にはアクセスしない等）を明記。
  - ルックアヘッドバイアス防止（target_date 時点のデータのみを使用、fetched_at の記録等）について明記。

Security
- RSS パースに defusedxml を利用し XML 攻撃に対処（news_collector）。
- ニュース URL 正規化によりトラッキングパラメータを除去。
- input の検証や欠損値チェック（数値の finite 判定、horizons のバリデーション等）を多数追加し不正入力の影響を抑制。

Notes / Known limitations
- execution および monitoring パッケージは骨格のみ（実装は今後の対応）。
- signal_generator の未実装事項（ドキュメント参照）
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有日数上限）
- news_collector の一部動作（INSERT RETURNING で正確に挿入数を返す等）は docstring に記載されているが、実際の DB スキーマ・実行環境に依存するため調整が必要。
- J-Quants クライアントは urllib を用いた実装のため、将来的に requests 等の利用や非同期化を検討。

導入方法・環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可; デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH / SQLITE_PATH (デフォルト設定あり)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

以上。今後のリリースでは execution/monitoring の実装、テスト・CI の追加、非同期処理やパフォーマンス最適化、さらに詳細なドキュメント・サンプルを予定しています。