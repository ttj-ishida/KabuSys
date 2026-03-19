Keep a Changelog 準拠の CHANGELOG.md（日本語）

全履歴は重要な変更点のみをコードベースから推測して記載しています。

Unreleased
---------

- （現在なし）

[0.1.0] - 2026-03-19
-------------------

Added
- 初回リリース: kabusys パッケージを追加。
  - パッケージ公開 API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ で公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースを強化:
    - export KEY=val 形式をサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープを解釈
    - インラインコメントの取り扱い（クォート有無に応じた振る舞い）
  - .env ファイル読み込み時の既存 OS 環境変数保護（protected set）と override フラグ対応。
  - Settings クラスを実装し、必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルト値（KABU_API_BASE_URL, DB パス等）を提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証（妥当でない値は ValueError を送出）。is_live / is_paper / is_dev プロパティを追加。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - 冪等な DuckDB への保存（ON CONFLICT を利用した UPDATE）。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行）、429 の Retry-After を考慮。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ。
    - save_* 関数での入力検証と PK 欠損行スキップ、fetched_at に UTC タイムスタンプを保存。
    - 型変換ユーティリティ (_to_float, _to_int)。

- ニュース収集（kabusys.data.news_collector）
  - RSS からの記事収集モジュールを追加（既定ソースに Yahoo Finance を設定）。
  - セキュリティ／堅牢化:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - 最大受信バイト数制限（10MB）によるメモリ DoS 緩和。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事IDのハッシュ化による冪等性確保。
    - 挿入時のチャンク化（INSERT のパラメータ数・SQL 長の上限対策）。
  - テキスト前処理（URL除去・空白正規化）や記事→銘柄紐付け（news_symbols）を設計に反映。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - モメンタム（mom_1m, mom_3m, mom_6m）、MA200 乖離（ma200_dev）計算。
    - ボラティリティ（20日 ATR / atr_pct）、平均売買代金、出来高比率。
    - バリュー（per, roe）計算（raw_financials から target_date 以前の最新財務データを取得して組み合わせ）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、結果を (date, code) キーの dict リストで返す。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンでの forward returns を一括クエリで取得。
    - IC（calc_ic）: ファクターと将来リターンの Spearman ランク相関を実装（同順位は平均ランク）。
    - 統計サマリー（factor_summary）と rank ユーティリティ（浮動小数点丸めで ties の検出漏れを抑制）。
  - research パッケージのエクスポートを整理（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュールの生ファクターを取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で差し替え（DELETE + bulk INSERT をトランザクションで実行し、原子性を確保）。
    - return: upsert した銘柄数を返す（冪等）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - Z スコアをシグモイド変換し、欠損コンポーネントは中立値 0.5 で補完。
    - 重みのマージ・検証・再スケール処理（ユーザ提供 weights の妥当性チェックを含む）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制。サンプル不足時は Bear とみなさない）。
    - BUY シグナルは final_score が閾値以上の銘柄を採用（Bear の場合は抑制）。
    - SELL シグナル（エグジット）判定を実装:
      - ストップロス（終値/avg_price - 1 <= -8%）を最優先
      - final_score が閾値未満の銘柄を SELL（positions に価格欠損がある場合はスキップ）
      - TODO としてトレーリングストップや時間決済は未実装（positions に peak_price / entry_date が必要）
    - signals テーブルへ日付単位で差し替え（トランザクションで原子性を確保）。
    - return: 書き込んだシグナル数（BUY + SELL）。

Changed
- （初回リリースのため過去からの変更はなし）

Fixed
- （リリース時点でのバグ修正履歴はなし）

Security
- ニュース収集で defusedxml を使用、RSS の受信サイズ制限や URL 正規化で SSRF/トラッキング対策を導入。
- .env 読み込みにおける OS 環境変数の保護（protected set）を実装し、テストや CI での予期せぬ上書きを防止。

Notes / Implementation details
- 多くの処理は DuckDB で SQL ウィンドウ関数を活用しており、パフォーマンスと一貫性を重視して設計されています。
- Look-ahead bias 防止のため、全ての計算・シグナル生成は target_date 時点で入手可能なデータのみを使用する設計方針を採用しています（fetched_at の記録や target_date 以前の最新価格参照など）。
- 一部の仕様（トレーリングストップ、時間決済など）は実装予定・未実装の旨コメントに記載あり。

今後の予定（推測）
- positions テーブルに必要なカラム（peak_price / entry_date 等）を追加してトレーリングストップや時間決済のエグジット条件を実装。
- news_collector の詳細な URL/SSRF 検査やソース拡張、記事→銘柄マッピングロジック強化。
- テスト・CI 整備、ドキュメント充実。

-----