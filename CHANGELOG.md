Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードから推測した追加機能、設計方針、安全装置、既知の動作などを記載しています。

CHANGELOG.md
-------------

すべての変更はセマンティックバージョニングに従います。  
詳細は Keep a Changelog を参照してください: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。モジュール構成は data, research, ai, config, などを含む。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env / .env.local）または OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml）を基に自動ロードを行い、カレントワーキングディレクトリに依存しない実装。
  - .env パーサ実装:
    - 空行／コメント行の無視、`export KEY=val` 形式のサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、クォートなしのインラインコメント処理。
  - 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - OS 環境変数を保護する `protected` 仕組みを採用し、.env.local による上書き時でも保護できる。
  - Settings クラスを提供し、以下の設定プロパティを安全に取得：
    - J-Quants / kabu API / Slack / データベースパス（DuckDB, SQLite）等。
  - 設定値バリデーション:
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の許容値チェック。
    - 必須値未設定時は ValueError を送出する `_require` を用意。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）により銘柄別センチメントを算出し ai_scores テーブルへ書き込む機能を実装。
  - 設計/実装上の主な点：
    - JST 基準のニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を計算する `calc_news_window`。
    - 1 銘柄あたり最大記事数／最大文字数でトリム（トークン肥大対策）。
    - 最大バッチサイズ（20 銘柄）でのバッチ送信。
    - OpenAI JSON mode を使った出力想定と、応答の厳密なバリデーション（JSON 抽出、results リスト、code と score の検証）。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ。
    - スコアは ±1.0 にクリップ。
    - 部分失敗時でも既存のスコアを必要以上に消さないよう、書き込みは該当コードのみ削除して再挿入（DELETE → INSERT、DuckDB の制約を考慮した executemany の実装）。
    - OpenAI 呼び出しをテストで差し替え可能な `_call_openai_api` の抽象化。
    - API キーが未設定の場合は ValueError を返す明示的エラー。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
  - 主な処理:
    - prices_daily から 200 日 MA 乖離を計算（ルックアヘッド防止のため target_date 未満のみを使用）。
    - raw_news のマクロキーワードでフィルタしてタイトルを取得し、LLM で macro_sentiment を評価（記事なし時は LLM 呼び出しを行わず macro_sentiment=0.0）。
    - OpenAI 呼び出しはリトライ／エラーハンドリングを行い、失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 合成スコアをクリップして regime_label を決定し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試み上位へ例外を伝播。
  - LLM の API 呼び出しは news_nlp と意図的に別実装にしてモジュール結合を低く維持。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（平均）、相対 ATR、20 日平均売買代金、出来高比などを計算。必要データ不足は None。
    - calc_value: raw_financials から最新財務データを取得し PER, ROE を計算（EPS 0/欠損時は None）。
    - 全て DuckDB (prices_daily / raw_financials) に対する SQL ベース実装、外部 API へは依存しない。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons のバリデーションあり。
    - calc_ic: Spearman のランク相関（Information Coefficient）計算。無効データやレコード数不足時は None。
    - rank: 同順位は平均ランクを返すランク関数（丸めにより ties の検出精度を担保）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリー。

- データ / カレンダー管理（kabusys.data.calendar_management）
  - 市場カレンダー（market_calendar）を扱うユーティリティを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar がない場合は曜日ベース（土日）でフォールバック。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した判定を返す設計。
    - 最大探索上限を設けて無限ループを防止（_MAX_SEARCH_DAYS）。
  - calendar_update_job: J-Quants API（jquants_client 経由）から差分でカレンダーを取得して保存する夜間バッチを実装。バックフィル（直近数日を再フェッチ）や健全性チェック（将来日付の異常検出）を行う。
  - jquants_client 経由での fetch / save 呼び出しを想定している。

- ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
  - ETLResult データクラスを公開し、ETL の実行結果（取得数、保存数、品質問題、エラー等）を一元化。
  - ETL ヘルパー: テーブル存在確認、最大日付取得などのユーティリティを実装。
  - 設計上、差分フェッチ・バックフィル・品質チェックの仕組みを意識した構造。

- エクスポート / 名前空間整理
  - ai, research, data パッケージ内で主要な関数を __all__ でエクスポート（例: score_news, score_regime, calc_momentum 等）。
  - data.etl は ETLResult を再エクスポート。

### 変更 (Changed)
- 初回リリースにつき履歴なし。

### 修正 (Fixed)
- ルックアヘッドバイアス防止:
  - AI・リサーチ・ETL 等のモジュールで datetime.today() / date.today() を直接参照せず、外部から与えた target_date に基づいて処理する方針を採用（再現性・バックテスト安全性を確保）。
- DuckDB 互換性考慮:
  - executemany に空リストを渡せない制約（DuckDB 0.10）への対応処理を実装し、空リスト時は実行をスキップするようにした。

### 既知の問題 / 注意点 (Known issues / Notes)
- OpenAI API を利用する全機能は API キー（OPENAI_API_KEY）が必要。未設定時は ValueError を送出するため呼び出し側で適切に設定すること。
- OpenAI 呼び出しは外部サービス依存のため、ネットワーク障害や API 仕様変更に対して脆弱。ライブラリはリトライ・フォールバック（0.0 返却）を実装しているが、完全な可用性は保証されない。
- .env パーサは多くのケースを想定しているが、極端に複雑な .env 書式（改行を含む値など）には対応していない可能性あり。
- DuckDB の日付型戻り値は実環境により文字列等で返る場合があるため、日付変換ユーティリティを用いて安全に date オブジェクトに変換している。
- calendar_update_job / pipeline 等は jquants_client の実装に依存。テスト時は該当クライアントをモックすること。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため無し。

---

開発者メモ:
- 将来的な改善候補:
  - ai モジュールの LLM 呼び出し部分を共通ライブラリに抽出して再利用性を高める（現状は意図的に分離済み）。
  - .env パーサのテストカバレッジ拡張（角ケースの検証）。
  - DuckDB バージョン差異によるバインド方法のさらなる抽象化。

---