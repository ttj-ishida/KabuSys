# Changelog

すべての注目すべき変更点はこのファイルに記載します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- Unreleased: 今後の変更（ない場合は空）
- 各リリースはバージョンと日付を付記し、カテゴリごとに要約します。

[Unreleased]

[0.1.0] - 2026-03-20
- Added
  - パッケージ初期公開として以下の主要機能を実装・追加しました。
    - kabusys パッケージの公開API
      - パッケージバージョン __version__ = "0.1.0"
      - __all__ に data, strategy, execution, monitoring を公開
    - 環境設定管理 (kabusys.config)
      - .env ファイルおよび環境変数を読み込む自動ローダーを実装
      - プロジェクトルート探索（.git または pyproject.toml を基準）によりカレントディレクトリ依存性を排除
      - 読み込み優先順位: OS環境変数 > .env.local > .env
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
      - .env 行パーサ: export 構文対応、シングル／ダブルクォート内のエスケープ処理、インラインコメント処理等の堅牢な実装
      - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベル等のプロパティを提供。必須変数未設定時は明示的に ValueError を送出
    - Data 層 (kabusys.data)
      - J-Quants API クライアント (jquants_client)
        - ページネーション対応で日足・財務・マーケットカレンダーを取得
        - 固定間隔スロットリングによるレート制限管理（120 req/min）
        - リトライ（指数バックオフ、最大3回）と 408/429/5xx に対する再試行処理
        - 401 発生時のトークン自動リフレッシュ（1 回のみ）と ID トークンのモジュールレベルキャッシュ共有
        - ペイロード受信と JSON パースの例外処理
        - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
          - fetched_at を UTC ISO8601 で保存
          - ON CONFLICT DO UPDATE による冪等保存
          - PK 欠損行のスキップとログ警告
          - 型変換ユーティリティ（_to_float, _to_int）
      - ニュース収集モジュール (news_collector)
        - RSS フィード取得 → 前処理 → raw_news へ冪等保存のワークフローを実装
        - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保
        - defusedxml を用いた XML 攻撃対策、HTTP スキーム検証等の安全対策
        - 受信サイズ制限（MAX_RESPONSE_BYTES）とトラッキングパラメータ除去、URL 正規化、複数レコードのチャンク挿入などの実装
    - Research 層 (kabusys.research)
      - ファクター算出モジュール (factor_research)
        - モメンタム（1M/3M/6M, MA200 乖離）、ボラティリティ（20日 ATR, atr_pct）、流動性（20日平均売買代金, 出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して算出
        - 各関数は (date, code) をキーとした dict のリストを返す設計
      - 解析ユーティリティ (feature_exploration)
        - 将来リターン計算 (calc_forward_returns)（複数ホライズン対応、存在しない場合は None）
        - IC（Spearman の ρ）計算 (calc_ic)、ランク変換ユーティリティ (rank)
        - ファクター統計サマリー (factor_summary)
      - zscore_normalize を外部に公開（kabusys.data.stats を経由）
    - Strategy 層 (kabusys.strategy)
      - 特徴量エンジニアリング (feature_engineering.build_features)
        - research 側で計算された生ファクターを統合、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
        - 指定カラムを Z スコア正規化し ±3 でクリップ
        - features テーブルへ日付単位で冪等（DELETE → INSERT、トランザクションで原子性確保）
      - シグナル生成 (signal_generator.generate_signals)
        - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
        - シグモイド変換／欠損は中立 0.5 で補完、重み付け合算で final_score を算出（デフォルト閾値 0.60）
        - Bear レジーム判定（ai_scores の regime_score 平均が負、かつサンプル数閾値を満たす場合）で BUY を抑制
        - 保有ポジションのエグジット判定（ストップロス -8% / final_score が閾値未満）を実装
        - BUY/SELL を signals テーブルへ日付単位で置換（トランザクションで原子性確保）
        - 重み辞書の検証・正規化（未知キー・非数値は無視、合計が 1 でない場合はリスケール）
- Changed
  - （初回リリースのため該当なし）
- Fixed
  - （初回リリースのため該当なし）
- Security
  - news_collector で defusedxml を採用、RSS パーシング時の XML 攻撃対策を導入
  - ニュース収集で外部 URL のスキーム検証や受信サイズ制限を実装し SSRF / DoS のリスクを軽減
- Notes / 実装上の設計意図（ドキュメント化）
  - ルックアヘッドバイアス回避: すべての戦略・研究コードは target_date 時点のデータのみ参照するよう設計
  - 発注層（execution）やモニタリング（monitoring）は戦略層から独立させ、依存を持たない設計
  - DuckDB 側のトランザクション（BEGIN/COMMIT/ROLLBACK）を用いて日付単位の置換処理で原子性を確保
  - ロギングを多用し警告・情報を明示的に記録（例: データ欠損・PK 欠損行のスキップ・ロールバック失敗の警告等）
  - 一部の追加仕様（例: トレーリングストップ、時間決済など）は positions テーブル側の追加情報（peak_price / entry_date 等）が必要であり現時点では未実装

今後の予定（例）
- execution 層の実装（kabuステーション API 連携）
- monitoring 層の実装（Slack 通知・監視ジョブ）
- テストカバレッジの拡充、CI 統合、ドキュメントの整備

---