# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に従います。  

次の慣例に従います: 日付は YYYY-MM-DD、各リリースには主要カテゴリ（Added, Changed, Fixed, Security, etc.）を付与します。

## [0.1.0] - 2026-03-19

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
  - settings/設定管理（src/kabusys/config.py）
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - OS 環境変数を保護する protected オプション、.env と .env.local の優先順（.env.local が上書き）を実装。
    - 必須設定取得ヘルパー _require、env 値検証（KABUSYS_ENV, LOG_LEVEL）と利便性プロパティ（is_live 等）を提供。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や kabu / Slack 関連設定の取得をサポート。
  - データ収集・保存
    - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
      - 固定間隔のレートリミッタ（120 req/min）、リトライ（指数バックオフ、最大3回）、特定ステータスに対する再試行ロジック実装。
      - 401 発生時の自動トークンリフレッシュ（1回のみ）を実装。ページネーション対応（pagination_key の共有）。
      - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。ON CONFLICT を用いた更新処理で重複を排除。
      - 入力変換ユーティリティ（_to_float / _to_int）を実装して不正データに対処。
    - ニュース収集モジュール（src/kabusys/data/news_collector.py）
      - RSS フィード収集の骨格を実装。既定ソース（Yahoo Finance）の設定を提供。
      - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）や記事IDの生成方針（正規化後SHA-256 の先頭32文字）を導入。
      - 受信サイズ制限（MAX_RESPONSE_BYTES）、XML パースに defusedxml を使用するなどセキュリティ対策を実装。
      - バルク INSERT のチャンク処理を実装しパフォーマンスに配慮。
  - リサーチ（研究）機能
    - ファクター計算モジュール（src/kabusys/research/factor_research.py）
      - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高比率）、Value（PER, ROE）などの計算関数を実装。prices_daily / raw_financials を参照して結果を (date, code) ベースで返す。
      - スキャン範囲や欠損扱い（データ不足時は None）など現実的な扱いを実装。
    - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns：任意ホライズンの一括取得、営業日→カレンダー日バッファ）、IC 計算（Spearman の ρ）、カラム統計サマリ（factor_summary）を実装。
      - ランク計算時の ties 処理（平均ランク）と数値丸めでの安定化を実装。
    - research パッケージのエクスポートを追加（src/kabusys/research/__init__.py）。
  - 戦略（strategy）機能
    - 特徴量生成モジュール（src/kabusys/strategy/feature_engineering.py）
      - research の生ファクターを結合・ユニバースフィルタ（最小株価・最低平均売買代金）適用、Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 クリップを行い、features テーブルへ日付単位の置換（トランザクション）で保存する build_features を実装。冪等性を確保。
    - シグナル生成モジュール（src/kabusys/strategy/signal_generator.py）
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して重み付き合算により final_score を算出する generate_signals を実装。
      - デフォルト重みと閾値（0.60）を実装。ユーザー指定の weights の検証・補完・リスケーリングに対応。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値）を導入し、Bear 時は BUY を抑制。
      - エグジット条件（ストップロス -8% / スコア低下）を実装。保有ポジションの価格欠損時は判定をスキップして安全性を確保。
      - signals テーブルへの日付単位の置換（トランザクション）で出力。SELL 優先ルール（SELL 対象は BUY から除外）を適用。
    - strategy パッケージエクスポート（src/kabusys/strategy/__init__.py）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- news_collector は defusedxml を利用して XML 関連攻撃（XML Bomb 等）に対処。
- RSS 取得時に HTTP/HTTPS スキームのみを扱う運用方針（実装方針に明記）。受信最大バイト数を制限してメモリ DoS を防止。
- J-Quants クライアントはネットワーク・HTTP エラーに対して再試行・バックオフを実装し、429 の Retry-After ヘッダを尊重。401 はトークンリフレッシュを試行して安全に回復を図る。

### Notes / Implementation details
- DB 書き込みは各所でトランザクション（BEGIN/COMMIT/ROLLBACK）＋バルク挿入を用い、原子性と効率を確保。ROLLBACK が失敗した場合のロギング処理も追加。
- .env パーサはエスケープされたクォート処理やインラインコメントの処理など、実運用で遭遇する様々なフォーマットに堅牢に対応するように設計。
- ファクター・シグナル計算はルックアヘッドバイアス防止のため target_date 時点のデータのみを参照するよう意識して実装。
- 多くの関数で欠損・非数値（NaN/Inf）チェックを徹底し、欠損値は None として扱い中立値で補完することで銘柄の不公平な扱いを防止。

### Known limitations / TODO
- strategy の一部エグジット条件（トレーリングストップ、時間決済）は comments に未実装として記載（positions テーブルに peak_price / entry_date 等が必要）。
- news_collector の記事パース・シンボル紐付け（news_symbols）実装の詳細は骨格が示されているが、外部ソース固有の処理やマッピングロジックは今後精緻化が必要。
- 単体テスト・統合テストの追加、および外部 API 呼び出し部分のモック化が推奨される。

---

今後のリリースでは、運用での実データ確認に基づく改善（ファクター調整、AI スコア連携、execution 層の統合、監視/アラート機能など）を予定しています。