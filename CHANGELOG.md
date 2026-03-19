CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と
「セマンティックバージョニング (SemVer)」の考え方に準拠します。

フォーマット: 日本語、重要な変更をカテゴリ別に記載します。

Unreleased
----------

（現在該当なし）

v0.1.0 - 2026-03-19
-------------------

初回リリース。本バージョンで導入した主要機能・実装・設計上の注意点をまとめます。

Added
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
  - public API エクスポート: kabusys パッケージは data, strategy, execution, monitoring を公開（execution, monitoring はモジュール雛形）。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - コメント処理（クォート内は無視、非クォートは '#' の直前がスペース/タブでコメントと判定）。
  - Settings クラスを提供し、必須値チェック・妥当性検証を実装:
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - DBパスのデフォルト（duckdb/sqlite）と Path 変換。
    - KABUSYS_ENV の許容値検証 (development, paper_trading, live) と補助プロパティ is_live/is_paper/is_dev。
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- データ取得・永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限 (120 req/min)。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して一度だけリトライ。
    - ID トークンはモジュールレベルでキャッシュしページネーション間で共有。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - ON CONFLICT DO UPDATE による冪等性確保。
    - 型変換補助関数 _to_float / _to_int を実装（厳密な変換ルール）。
    - PK 欠損レコードはスキップし、スキップ件数をログ出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装。
  - URL 正規化 (トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化) を提供。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等を防止。
    - HTTP/HTTPS スキームに限定（SSRF 軽減設計の方針）。
    - 最大受信サイズ（10 MB）でメモリ DoS を緩和。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）などを想定して冪等性を確保。
  - バルク INSERT のチャンク化（チャンクサイズ 1000）で DB 負荷を制御。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算の参照実装を公開:
    - calc_momentum / calc_volatility / calc_value を提供（prices_daily / raw_financials を参照）。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 将来リターンを複数ホライズン（デフォルト [1,5,21]）で計算。リード関数を使った一括取得でパフォーマンス配慮。
    - calc_ic: スピアマンランク相関（IC）を計算。ties は平均ランクで処理、サンプル数 3 未満は None を返す。
    - rank: 同順位は平均ランク、round(..., 12) による丸めで ties 検出漏れを低減。
    - factor_summary: count/mean/std/min/max/median を算出（None と非有限値を除外）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で作成した raw factor を統合して features テーブルへ書き込む build_features を実装。
  - 処理概要:
    - calc_momentum / calc_volatility / calc_value の出力をマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）を適用。
    - 指定列（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - 日付単位で DELETE → INSERT（トランザクションで原子性確保）し冪等に保存。
  - ロギングとエラー時のロールバック対処を実装。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し signals テーブルへ保存する generate_signals を実装。
  - 実装の主な点:
    - コンポーネントスコア:
      - momentum: momentum_20/momentum_60/ma200_dev をシグモイド変換して平均化。
      - value: PER（小さいほど高評価）を 1/(1+per/20) でマッピング。
      - volatility: atr_pct の Z スコアを反転してシグモイド変換。
      - liquidity: volume_ratio をシグモイド変換。
      - news: ai_scores.ai_score をシグモイド変換、未登録は中立補完。
    - デフォルト重みと閾値:
      - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。
      - デフォルト BUY 閾値: 0.60。
      - ユーザー指定 weights は検証（非数値/負値/NaN/Inf を無視）、既定キーのみ受け付け、合計が 1.0 でない場合はリスケール。
    - Bear レジーム判定:
      - ai_scores の regime_score の平均が負で且つサンプル数 >= 3 の場合に Bear と判定し BUY を抑制。
    - エグジット判定（SELL シグナル）:
      - ストップロス（現在値/平均取得単価 - 1 <= -8%）。
      - final_score が閾値未満。
      - 価格欠損銘柄は SELL 判定の判定自体をスキップし、features に存在しない保有銘柄は final_score=0.0 と扱う。
      - 未実装（注記）: トレーリングストップ、時間決済（要 positions テーブルの peak_price/entry_date）。
    - 日付単位の DELETE → INSERT をトランザクションで行い冪等性を確保。エラー時のロールバックに対するログ出力あり。

Changed
- (なし: 初回リリース)

Fixed
- (なし: 初回リリース)

Deprecated
- (なし)

Removed
- (なし)

Security
- ニュース収集モジュールで defusedxml を採用し XML 関連の攻撃対策を実施。
- RSS 取得時に HTTP/HTTPS 以外のスキームを拒否する方針（SSRF 緩和）。
- J-Quants クライアントはリクエスト制御とリトライ制御を備え、429 の Retry-After を尊重。

Known limitations / Notes
- execution / monitoring パッケージはエントリポイントを用意しているが、本バージョンでは発注（kabu API）や監視ロジックの実装は含まれていない（モジュール雛形）。
- signal_generator にてトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date の保持が必要）。
- zscore_normalize 関数は kabusys.data.stats モジュール側で提供されていることを前提としている（このリリースでは参照実装を利用）。
- 一部 SQL は DuckDB のウィンドウ関数や LEAD/LAG を利用しており、対象 DB が DuckDB であることが前提。
- .env 自動ロードはプロジェクトルートの探索に依存するため、配布後や非標準配置での運用時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動設定することを推奨。

今後の予定（案）
- execution 層: kabuステーション API との連携実装（注文送信・注文管理）。
- monitoring 層: Slack 通知や監視ダッシュボード統合。
- signal_generator の追加ルール（トレーリングストップや時間決済）の実装。
- テストカバレッジの追加、CI の整備。

以上。