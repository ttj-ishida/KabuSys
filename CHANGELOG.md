# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成したもので、実装上の設計方針・既知の制約・セキュリティ関連の注意点も含みます。

すべてのバージョンは SemVer（パッケージの __version__ に基づく）に従います。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」のコア機能をまとめて実装しています。以下は実装済みの主な機能・設計方針・既知の制約です。

### Added
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"`
  - パッケージの公開 API: `data`, `strategy`, `execution`, `monitoring`（__all__）

- 設定 / 環境変数読み込み (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を上位ディレクトリから探索して自動ロードを行う（CWD に依存しない）。
  - .env パーサーは以下をサポート:
    - 空行・コメント行（行頭 `#`）の無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの値では inline コメント判定（`#` の直前にスペース/タブがある場合のみコメントと解釈）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - OS 環境変数を保護するための protected キー扱い（.env.local でも既存 OS 環境変数は上書きされない）
  - 自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを抑止可能
  - `Settings` クラスによりアプリ設定をプロパティで提供:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）等の必須/既定値を扱う
    - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の値検証（許可値以外は ValueError）
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装:
    - レート制限遵守（120 req/min、固定間隔スロットリング）
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）
    - 401 受信時は自動でリフレッシュトークンを使って ID トークンを更新し 1 回リトライ
    - ページネーション対応（pagination_key を利用）
    - 取得時刻（fetched_at）を UTC ISO8601 形式で付与（Look-ahead バイアスのトレースを意識）
  - DuckDB への保存関数（冪等性を確保）:
    - save_daily_quotes: raw_prices への保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials への保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar への保存（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ: `_to_float`, `_to_int`（空値・不正文字列を安全に扱う）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集処理（デフォルトソースに Yahoo Finance を設定）
  - テキスト前処理（URL 除去、空白正規化）と URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を抑制
  - defusedxml を使った XML パースで XML-Bomb 等を防止
  - DB 保存はバルク挿入（チャンクサイズ上限）で効率化、ON CONFLICT DO NOTHING（冪等性）
  - 記事 ID の方針: 正規化 URL の SHA-256（先頭 32 文字）を想定（冪等性確保） — ドキュメントに明記

- リサーチ系ユーティリティ (`kabusys.research`)
  - ファクター計算（`factor_research`）:
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - Volatility（atr_20、atr_pct、avg_turnover、volume_ratio）
    - Value（per、roe を raw_financials と prices_daily から算出）
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し外部 API に依存しない
  - 特徴量分析（`feature_exploration`）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）
    - IC（Information Coefficient: スピアマン ρ）計算（calc_ic）
    - 基本統計サマリー（factor_summary）
    - 独自ランク関数（rank、同順位は平均ランク）
  - z-score 正規化ユーティリティは `kabusys.data.stats.zscore_normalize` を利用（モジュール内で参照）

- 戦略実装（strategy）
  - 特徴量エンジニアリング（`strategy.feature_engineering.build_features`）
    - research の生ファクターを取得 → ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）適用 → 指定列を Z スコア正規化（列集合は定義済み）→ ±3 でクリップ → features テーブルへ日付単位で置換（トランザクションで原子性）
    - 休場日や当日の欠損に配慮して target_date 以前の最新価格を参照
  - シグナル生成（`strategy.signal_generator.generate_signals`）
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントの補完方針: 欠損値は中立 0.5 で置換
    - 最終スコアは重み付き合算（デフォルト重みを持ち、ユーザー指定重みは検証・正規化される）
    - BUY 閾値デフォルト 0.60、Bear レジーム時は BUY を抑制（レジーム判定は ai_scores の regime_score 平均が負の場合、ただしサンプル数閾値あり）
    - エグジット判定（SELL）:
      - ストップロス: 現在終値 vs avg_price が -8% 以下 → SELL（最優先）
      - スコア低下: final_score が threshold 未満 → SELL
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入、冪等）

### Security
- defusedxml を用いた RSS XML の安全パースを導入（XML エンティティ攻撃の緩和）
- ニュース収集での URL 正規化とトラッキングパラメータ削除により同一記事の重複登録を抑制
- RSS/HTTP 受信での最大バイト制限（10MB）を導入
- J-Quants クライアントで Authorization ヘッダを管理し、トークン更新時の無限再帰を防止（allow_refresh フラグ）

### Performance / Reliability
- API 呼び出しの固定間隔スロットリングでレート制限を確実に遵守（120 req/min）
- 重要な DB 操作はトランザクションで包み、失敗時は ROLLBACK を試みてログ出力
- 保存処理は ON CONFLICT DO UPDATE / DO NOTHING を用いて冪等性を担保
- ページネーション時にトークン共有（モジュールレベルキャッシュ）で複数ページを効率的に取得

### Known issues / Limitations
- ニュースモジュールの一部（記事ID生成や銘柄紐付け（news_symbols）など）はドキュメント方針に言及されているが、提供コード断片では実装の続きを要する箇所がある（URL 正規化関数の途中まで実装が見える）。実運用前に全機能の完成度を確認してください。
- ポジション情報（positions テーブル）に peak_price / entry_date 等の列が必要な一部ロジック（トレーリングストップ、時間決済）は未実装。ドキュメントには将来的な実装予定が示されている。
- AI スコア関連:
  - ai_scores 未登録の銘柄はニューススコアを中立（0.5）で補完する設計のため、AI スコアがない場合でも銘柄が過度に不利にならないようになっているが、AI スコア運用方針は別途検討が必要。
  - Bear 判定は最低サンプル数（3）未満の場合は Bear としない（誤判定防止）が、その閾値は運用上のチューニングが必要。
- 外部 API（kabu ステーションの注文実行層など）との連携は execution モジュール配下に想定されているが、このリリースでは発注 API への直接依存は持たない（分離された設計）。発注実装は別途実装が必要。
- 単体テスト・統合テストはこのスナップショットからは確認できないため、リリース前にテスト整備を推奨。

### Internal / Developer notes
- 多くの処理で DuckDB を前提とした SQL を使用（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のスキーマが想定される）
- 設計方針として「ルックアヘッドバイアス防止」「発注層とロジック層の分離」「冪等性の確保」が一貫して採用されている
- ロギングが適切に組み込まれており、警告・情報レベルのログで異常検知がしやすい設計

---

もし CHANGELOG に追加したい運用ポリシー（リリース日をプロジェクト日付に合わせる、Unreleased セクションの運用方法、既知の issue トラッキング番号の添付など）があれば教えてください。必要に応じて各リリースノートをより詳細に分割（data/*, research/*, strategy/*, security）して出力します。