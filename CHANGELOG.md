# Changelog

すべての重要な変更をここに記録します。このファイルは Keep a Changelog の形式に準拠しています。  
リリースは逆順（最新が上）で記載されています。

※本文は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報 (src/kabusys/__init__.py) にて公開モジュールを定義。

- 環境設定/ローダー (src/kabusys/config.py)
  - .env ファイル自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート（テスト用）。
  - .env のパース実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、コメント処理）。
  - protected オプションによる OS 環境変数保護（上書き防止）。
  - Settings クラスによるアプリケーション設定の公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
    - DUCKDB_PATH / SQLITE_PATH のデフォルト値と Path オブジェクト返却
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1 銘柄あたりの最大記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - JSON Mode を使用した厳密な JSON レスポンス期待とレスポンス復元（前後余分テキストの {} 抽出）。
  - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装（_MAX_RETRIES）。
  - レスポンスのバリデーション（results 配列・code と score の検査、スコアを ±1.0 にクリップ）。
  - 書き込みは部分的保護: スコア取得済みコードのみ DELETE → INSERT で置換（DuckDB executemany の空パラメータ制約を考慮）。
  - テスト用に _call_openai_api をモック可能。

- AI / 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）判定。
  - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）、データ不足時は中立（1.0）扱い。
  - マクロニュース抽出はキーワードリストによるフィルタ、記事なしの場合は LLM 呼び出しをスキップ。
  - OpenAI 呼び出しは gpt-4o-mini、JSON Mode、リトライ/バックオフ実装。API 失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず続行）。
  - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK とログ）。

- データプラットフォーム - カレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar を用いた営業日判定ロジック:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
  - DB に値があれば優先、未登録日は曜日ベース（土日を休日）でフォールバックする設計により DB がまばらでも一貫した結果を返す。
  - next/prev_trading_day は最大探索範囲を制限（_MAX_SEARCH_DAYS）して無限ループを防止。
  - calendar_update_job により J-Quants API から差分を取得し、バックフィル・健全性チェック（未来日過度検出）して保存。J-Quants クライアントとの接続は jquants_client 経由。

- データプラットフォーム - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を公開（ETL の実行結果、品質チェックやエラー一覧を保持、辞書化可能）。
  - 差分取得・保存・品質チェックのフレームワーク（jquants_client と quality モジュールを利用する想定）。
  - 初期ロード用最小日付、カレンダー先読み、バックフィル日数等の定数を定義。
  - 内部ユーティリティ: テーブル存在チェック、最大日付取得等。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - factor_research.calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（prices_daily を参照）。
  - factor_research.calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR と移動平均）。
  - factor_research.calc_value: per / roe を raw_financials と prices_daily から計算（最新財務レコードを target_date 以前で取得）。
  - feature_exploration.calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算（LEAD を利用）。
  - feature_exploration.calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（None/不足データは適切に扱う）。
  - feature_exploration.rank: 同値は平均ランクで処理（丸めで ties 検出漏れ防止）。
  - feature_exploration.factor_summary: count/mean/std/min/max/median の統計サマリを標準ライブラリのみで実装。

- データモジュールの設計方針や注意点（コード内 docstring と実装に明示）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() をデータ計算関数内部で参照しない設計。
  - DuckDB を主要なデータバックエンドとして想定。
  - 本番注文系（kabu API 等）へのアクセスは研究/解析関数から一切行わない（安全分離）。

### Changed
- 新規リリースのため該当なし（初回リリース）。

### Fixed
- 新規リリースのため該当なし（初回リリース）。ただし、API 呼び出しや DB 書き込みに関する多くのフォールバック・例外処理を実装して堅牢性を確保している。

### Security
- センシティブな API キーやトークンは Settings 経由で環境変数から取得する設計。自動 .env ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Implementation details (設計上の重要点)
- OpenAI（gpt-4o-mini）を JSON Mode で使用し、レスポンスは厳密な JSON を期待するが、実装側で前後余計なテキストを取り除く復元を行う。
- LLM 呼び出しはリトライ戦略（429, ネットワーク断, タイムアウト, 5xx）を実装し、重大障害でもシステム全体を停止させない（フェイルセーフ）。ただし、API キー未設定時は ValueError を発生させる設計。
- DB 書き込みは冪等性を考慮（DELETE → INSERT、トランザクション、失敗時に ROLLBACK 実施）。
- DuckDB の executemany における空リストバインドの挙動に配慮して、空チェックを行ってから実行する。
- テスト容易性のため OpenAI 呼び出しをラップした内部関数を用意し、ユニットテストで差し替え可能にしている。

---

今後のリリース案内（例）:
- AI モデル差し替えの抽象化、Mock クライアントの提供
- jquants_client の実装/スタブ化と統合テスト
- ETL のスケジューリング / 監視ジョブの追加
- kabu ステーションとの発注・実行モジュール（現在はパッケージ公開のみ）

--- 

（以上）