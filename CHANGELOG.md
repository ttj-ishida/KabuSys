# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

- 変更履歴ではセマンティックバージョニングを使用しています。
- このファイルはコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・統合しました。

### 追加 (Added)
- パッケージの基本情報
  - パッケージルート: `kabusys`、バージョン `0.1.0` を定義。
  - エクスポート: `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数を読み込む自動ローダを実装（プロジェクトルート検出： `.git` または `pyproject.toml` を基準）。
  - `.env` / `.env.local` の読み込み順を定義（OS 環境変数 > .env.local > .env）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env の行パーサ `_parse_env_line` を実装：
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
  - 設定アクセス用 `Settings` クラスを提供（例: `settings.jquants_refresh_token`、`settings.kabu_api_password`、`settings.slack_bot_token` など）。
  - 環境値検証（`KABUSYS_ENV`, `LOG_LEVEL` の有効値チェック）を実装。

- データ取得・保存（J-Quants API クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API 呼び出しユーティリティ `_request` 実装：
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx をリトライ対象。
    - 401 エラー時はリフレッシュトークンによる ID トークン再取得を自動で試行（1 回のみ）。
    - 429 の場合は `Retry-After` ヘッダを優先。
  - トークン管理：モジュールレベルの ID トークンキャッシュと `get_id_token` を提供。
  - ページネーション対応のデータフェッチ関数を実装：
    - `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`
  - DuckDB へ冪等保存する関数を実装：
    - `save_daily_quotes`（raw_prices へ ON CONFLICT DO UPDATE）
    - `save_financial_statements`（raw_financials へ ON CONFLICT DO UPDATE）
    - `save_market_calendar`（market_calendar へ ON CONFLICT DO UPDATE）
  - 入力の型安全変換ユーティリティ `_to_float`, `_to_int` を実装。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS 取得から前処理、DB 保存までの処理を実装。
  - 記事ID の冪等化のため URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）を実装。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）。
  - 受信サイズ上限（10 MB）や SSRF を意識した URL 検査など、セキュリティ・堅牢性の考慮。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- 研究 (Research) モジュール (`kabusys.research`)
  - ファクター計算・探索機能を実装・公開：
    - `calc_momentum`, `calc_volatility`, `calc_value`（`kabusys.research.factor_research`）
    - `zscore_normalize` を `kabusys.data.stats` から再輸出
    - `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`（`kabusys.research.feature_exploration`）
  - 将来リターン計算（`calc_forward_returns`）：複数ホライズンを同時に取得する最適化クエリ。
  - Spearman ランク相関（IC）計算（`calc_ic`）とランク関数（同順位は平均ランク処理）を実装。
  - ファクターベースの統計サマリー（count/mean/std/min/max/median）を提供。

- 戦略 (Strategy) モジュール
  - 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
    - 研究で計算した raw factors をマージ、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 正規化（Z スコア）と ±3 でのクリッピング、features テーブルへの日付単位の置換（冪等）。
    - DuckDB トランザクションを使った原子性確保（DELETE -> INSERT の置換）。
  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - features と ai_scores を統合して最終スコア（final_score）を計算。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算（デフォルト重みあり）。
    - 重みの入力検証と合成（未知キー無視、非数値除外、合計が 1.0 でない場合の再スケール）。
    - Bear レジーム判定（AI の regime_score 平均が負の場合）による BUY 抑制。
    - SELL 条件（ストップロス -8%、スコア低下）を実装。SELL を優先して BUY を除外。
    - signals テーブルへの日付単位の置換（トランザクション + バルク挿入）。
    - 最終的に書き込んだシグナル数を返す。

- その他の実装
  - DuckDB を前提としたクエリ・集約実装全般（prices_daily / raw_financials / features / ai_scores / positions 等を参照）。
  - ロギング（各処理で情報・警告・デバッグログを出力）。

### 変更 (Changed)
- 初期実装のため大きな後方互換性変更はなし（このリリースがベースライン）。

### 修正 (Fixed)
- .env パーサで以下の解釈上の問題を考慮して実装を強化：
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの適切な扱い。
- J-Quants クライアントの再試行とトークンリフレッシュ周りで無限再帰や不必要なリトライを防ぐ保護（`allow_refresh` フラグ、1 回だけのトークン再取得）を導入。

### セキュリティ (Security)
- news_collector で defusedxml を利用して XML パースの安全性を確保。
- RSS URL 正規化・トラッキングパラメータ削除・受信サイズ制限により外部入力による攻撃リスクを軽減。
- J-Quants クライアントでタイムアウト、適切なエラーハンドリングを実装。

### 既知の制限 / TODO
- Strategy のエグジット条件（未実装項目）:
  - トレーリングストップ（peak_price の保持が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の URL 検証は強化済みだが、全ての SSRF パターンを網羅しているわけではないため運用での監視が推奨されます。
- 外部依存の最適化（並列取得、永続レートリミッタの共有など）は今後の改善候補。

---

今後のリリースでは、エグジットロジックの拡充、execution 層との連携（発注API統合）、テストカバレッジ強化、及び運用用の監視/メトリクス機能追加が想定されます。