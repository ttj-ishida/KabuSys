# CHANGELOG

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
このリポジトリの初期リリース（v0.1.0）に含まれる主要な追加機能、設計方針、既知の制限点を日本語でまとめています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- セキュリティ (Security)
- 注意事項 / 既知の未実装 (Known limitations / Notes)

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-03-19
初期公開リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にルートを探索する機能を実装。CWD に依存しない自動ロード。
  - .env 読み込みロジック:
    - .env と .env.local を読み込み、OS 環境変数を保護する仕組み（.env.local は override=True）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
    - export KEY=val、シングル／ダブルクォート、エスケープ、インラインコメントの取り扱いに対応するパーサを実装。
  - 必須変数チェック（_require）を実装し、未設定時は ValueError を送出するプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
  - 設定値の検証:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - DBパスの便利プロパティ（duckdb/sqlite）を提供。

- データ取得・保存（J-Quants クライアント）(src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - 汎用リクエスト関数（_request）にリトライ（指数バックオフ、最大3回）、429 の Retry-After 考慮、ネットワークエラーの再試行、401 の自動トークンリフレッシュ（1回）を実装。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への冪等保存関数（ON CONFLICT を利用）:
      - save_daily_quotes (raw_prices)、save_financial_statements (raw_financials)、save_market_calendar (market_calendar)
    - 型変換ユーティリティ: _to_float, _to_int（安全な変換ロジック）。
    - ID トークンキャッシュによるページ間のトークン共有。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存する処理を実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化: トラッキングパラメータ（utm_*、fbclid 等）の除去、クエリソート、フラグメント除去、スキーム/ホスト小文字化。
  - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、XML の安全パーシング（defusedxml）、SSRF 回避の設計方針を記載。
  - バルク INSERT のチャンク処理や INSERT RETURNING を想定した効率的 DB 保存戦略を採用。

- 研究用ファクター計算（research）(src/kabusys/research/*.py)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB から計算。
    - calc_volatility: 20日 ATR・atr_pct、20日平均売買代金(avg_turnover)、volume_ratio を計算。
    - calc_value: raw_financials と当日株価から PER / ROE を計算（最新財務レコードを取得）。
    - 実装は prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない方針。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得するクエリ実装。
    - calc_ic: Spearman（ランク相関）による IC 計算（ペアが 3 未満は None を返す）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにするランク関数を実装（丸めによる ties 対策あり）。
  - research パッケージのエクスポートを整理。

- 戦略（strategy）(src/kabusys/strategy/*.py)
  - feature_engineering.build_features:
    - research 側で算出した raw factors をマージし、ユニバース（最低株価/平均売買代金）フィルタを適用。
    - 指定カラムを zscore 正規化（kabusys.data.stats.zscore_normalize に依存）、±3 でクリップ。
    - 日付単位での置換（DELETE + バルク INSERT）により冪等性と原子性を保証（トランザクション）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損補完（None→中立0.5）を行い final_score を計算（デフォルト重みを採用、ユーザ指定重みは検証・正規化）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル >=閾値）時は BUY シグナルを抑制。
    - BUY/SELL シグナル生成、保有ポジションに対するエグジット判定（ストップロス、スコア低下）。
    - signals テーブルへの日付単位置換（DELETE + バルク INSERT）により冪等性と原子性を保証。
    - positions / prices_daily / features / ai_scores などの DB テーブルを参照。
  - strategy パッケージのエクスポートを整理。

- その他
  - ロギング、詳細なデバッグ情報、例外ハンドリング（トランザクションのROLLBACK処理と警告）の整備。
  - 多くの処理で「ルックアヘッドバイアス防止」の設計方針を明記（target_date 時点のデータのみ参照、fetched_at を UTC で記録等）。

### Security
- ニュース処理で defusedxml を使用し XML 関連攻撃（XML Bomb 等）に対処。
- ニュースの URL 正規化・スキーマチェックなどにより SSRF 対策の設計方針を盛り込む。
- J-Quants クライアントは 401 リフレッシュ処理、Retry-After 尊重、リトライ上限等を実装し堅牢化。

### Known limitations / Notes
- signal_generator のエグジット判定に関して、ドキュメントで言及されているが未実装の条件あり:
  - トレーリングストップ（ピーク価格管理）や時間決済（保有日数）については positions テーブル側で peak_price / entry_date 等の情報が必要であり現バージョンでは未実装。
- news_collector の説明・一部ユーティリティは実装済みだが、外部 HTTP フェッチ処理や DB への紐付け（news_symbols）の完全なフローは実装状況に依存（現状ファイル内の設計方針に従う）。
- zscore_normalize 等、いくつかのユーティリティは kabusys.data.stats モジュールに依存（別ファイルで提供されている前提）。
- DuckDB のスキーマ（テーブル定義: prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）は別途用意が必要。
- ネットワーク/外部 API 呼び出しのテストはモックや KABUSYS_DISABLE_AUTO_ENV_LOAD を使った環境分離を推奨。

### Migration / Upgrade notes
- 初期リリースのため、上位互換性の問題は特になし。今後のリリースでは signals/features テーブルのスキーマ変更や重みのデフォルト調整に注意。

---

今後の改善候補（例）:
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済）の実装。
- ニュース記事の NLP 前処理（トークン化・言語判定）や記事→銘柄の自動マッチング精度向上。
- tests（ユニット/統合）の拡充と CI の追加。
- パフォーマンス改善（bulk 処理の最適化、並列フェッチ等）。

（注: 上記はコードベースから推測可能な実装内容と設計方針に基づく CHANGELOG です。実際のリリースノートとして公開する際は必要に応じて日付・担当者・リファレンスを追加してください。）