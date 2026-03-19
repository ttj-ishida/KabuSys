# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはパッケージのコードベースから推測して作成した初回リリース向けの変更履歴です。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化。公開 API として data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを `0.1.0` に設定。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用）。
    - OS 環境変数は保護（上書き禁止）するよう保護キーセットをサポート。
  - .env パーサーの実装：
    - 空行・コメント行（#）の無視。
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント処理（# の直前がスペース/タブの場合のみコメントとみなす）。
  - Settings クラスを提供し、プロパティ経由で設定値を取得可能：
    - 必須項目は取得時に検査して未設定なら ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - DB パスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を用意。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のブールフラグ補助を提供。

- データ取得 / 保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を RateLimiter で管理。
    - HTTP リクエストラッパーにリトライ（指数バックオフ、最大 3 回）、特定ステータス（408/429/5xx）での再試行ロジックを実装。
    - 401 を検出した場合はリフレッシュトークンから ID トークンを自動再取得して 1 回だけリトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - 取得データを DuckDB に冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存時に fetched_at を UTC ISO8601 で記録。
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装し不正値は None に変換。
  - API 呼び出しの安全性・信頼性に配慮（タイムアウト、JSON デコード失敗時エラー化）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存する仕組み（DataPlatform.md に準拠した設計）。
  - 実装上の特徴：
    - RSS XML のパースに defusedxml を使用し XML による攻撃を軽減。
    - レスポンス受信サイズ上限（10 MB）を導入してメモリ DoS を防止。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 記事 ID は正規化した URL の SHA-256（先頭 32 文字）で一意化し冪等性を確保する設計（説明に記載）。
    - HTTP/HTTPS スキーム以外の URL 拒否、トラッキングパラメータのプレフィックス除去などの対策が記載。
    - バルク INSERT のチャンク処理やトランザクションまとめによる効率化。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリ RSS を設定。

- 研究用 / ファクター計算 (src/kabusys/research/*.py, src/kabusys/research/__init__.py)
  - ファクター計算モジュール（factor_research）を実装：
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を calc_momentum で計算。
    - Volatility（atr_20, atr_pct）、流動性（avg_turnover, volume_ratio）を calc_volatility で計算。
    - Value（per, roe）を raw_financials と prices_daily から calc_value で計算。
    - 各関数は DuckDB 接続（prices_daily / raw_financials）を受け取り、(date, code) ベースの dict リストを返す。
  - 特徴量探索モジュール（feature_exploration）を実装：
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用して一度に取得）。
    - calc_ic: factor と将来リターンのスピアマン順位相関（IC）を計算（有効サンプルが 3 未満なら None）。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（round(..., 12) による ties 対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
  - research パッケージは必要な関数を __all__ で公開。

- 戦略層 (src/kabusys/strategy/*.py)
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールで計算した生ファクターを取得し結合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 正規化対象カラムに対して z-score を適用（zscore_normalize を使用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（削除→挿入）する処理をトランザクションで実装（冪等）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算。
      - momentum/value/volatility/liquidity/news の各コンポーネントを計算するユーティリティを実装（sigmoid, per 転換等）。
      - PER の取扱い（非正または欠損は None）。
      - ai_score 未登録時はニューススコアを中立値で補完。
    - 最終スコア final_score を重み付け合算（デフォルト重みを提供）し、閾値（デフォルト 0.60）で BUY を決定。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数が十分な場合）では BUY を抑制。
    - エグジット（SELL）判定の実装：
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score が threshold 未満）
      - ※トレーリングストップや時間決済は未実装で注記あり（positions に peak_price / entry_date が必要）。
    - BUY と SELL を統合して signals テーブルへ日付単位で置換（トランザクション）する処理を実装。
    - weights に対する入力検証（非数値・負値などの無効値は無視、合計が 1 でない場合は再スケーリング）。

### 変更 (Changed)
- 初回リリースのため変更履歴はありません（新規追加のみ）。

### 修正 (Fixed)
- 初回リリースのため修正履歴はありません。

### 既知の制限 / 注意点 (Known issues / Notes)
- news_collector の説明には記事ID生成や記事と銘柄の紐付け方が設計として記載されているが、RSS フィード取得の詳細な実行部分や DB への完全な挿入処理の一部は実装ファイルの抜粋により未確認の箇所あり。
- signal_generator の一部のエグジット条件（トレーリングストップ、保有期間による決済）は未実装で、positions テーブルに追加情報が必要。
- .env パーサーの挙動（コメント除去ルールやクォート内エスケープ）は慎重に設計されているが、特殊ケースは運用での確認推奨。
- J-Quants クライアントはネットワーク・HTTP の再試行ロジックを備えるが、長期の API ポリシー変更や認証フロー変更には追従が必要。

---

リリースに関する補足や、特定モジュール（例: news_collector の残り実装や execution 層実装）について追記が必要でしたら、そのソース全体または差分を提示してください。さらに詳しいリリースノート（API 使用例・設定例・互換性注意点）も作成できます。