# Changelog

すべての重要な変更をここに記載します。本ファイルは Keep a Changelog のフォーマットに準拠します。バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

※日付は本コードベース解析時点（2026-03-29）を使用しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

### Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ構成: data, research, ai, execution（パッケージ公開対象）、monitoring（公開対象）を __all__ で指定（src/kabusys/__init__.py）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - export 形式やクォート・エスケープ、インラインコメントを考慮した .env パース実装。
  - OS 環境変数を保護する protected 上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境（development/paper_trading/live）やログレベルのバリデーションを実装。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini）でバッチセンチメント評価を行う score_news を実装。
  - チャンク処理（最大20銘柄）、1銘柄あたりの記事数・文字数制限、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ、DuckDB への冪等書き込み（DELETE → INSERT）を実装。
  - リトライ（429/ネットワーク断/タイムアウト/5xx）やフェイルセーフ（API失敗時はスキップして継続）を実装。テスト容易性のため _call_openai_api を差し替え可能。
  - タイムウィンドウ計算ユーティリティ calc_news_window を実装（JST 基準で前日 15:00 〜 当日 08:30 を UTC に変換）。
- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（TOPIX 日経系ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を算出する score_regime を実装。
  - マクロキーワードで raw_news をフィルタし LLM（gpt-4o-mini）を使用、冪等な DB 書き込みとリトライ・フェイルセーフを備える。
  - OpenAI キー注入（api_key 引数または環境変数 OPENAI_API_KEY）に対応。テスト用に内部 OpenAI 呼び出しを差し替え可能。
- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar に基づく is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が無い場合は曜日ベース（平日を営業日）でフォールバックするロジックを実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアントから差分取得 → 保存を行う。バックフィル・健全性チェックを導入。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装し、取得件数・保存件数・品質チェック結果・エラー一覧を管理。
    - 差分更新のための最大日付取得、テーブル存在チェック等ユーティリティを実装。
    - J-Quants クライアント（jquants_client）と品質チェックモジュール（quality）を組み合わせる設計方針を文書化。
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。
- リサーチ / ファクター（src/kabusys/research/*）
  - factor_research.py: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照し、モメンタム、ATR、出来高・売買代金、PER/ROE 等を算出。
  - feature_exploration.py: calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関 / IC）、rank（同順位は平均ランク）、factor_summary（基本統計）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ __init__ で主要関数を公開。
- テスト・運用を想定した設計（プロジェクト横断）
  - ルックアヘッドバイアス防止のため date.today()/datetime.today() を参照しない設計方針が各モジュールに明記。
  - OpenAI 呼び出しやタイムアウト処理は明示的に分離され、unittest.mock.patch による差し替えを想定。
  - DuckDB の executemany の制約（空リスト不可）への対応（事前チェック）や date 値の互換変換処理を実装。

### Changed
- 初回リリースのため該当なし（新規実装のみ）。

### Fixed
- 初期設計段階での堅牢性対策を多数実装（例: LLM のレスポンスパース失敗や API 5xx に対するリトライ、DB 書込み失敗時のロールバックと警告ログなど）。
- .env パーサーでのクォート・バックスラッシュエスケープ、インラインコメント処理を実装し、一般的な .env 形式の互換性を向上。

### Security
- OpenAI API キーや各種シークレットは Settings を通じて環境変数で取得する設計。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- 環境変数の上書きに対する protected 保護（OS 環境変数の誤上書きを防止）を実装。

### Notes / Known limitations
- OpenAI（gpt-4o-mini）利用部分は API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する仕様。
- ai モジュールは gpt の JSON mode を前提に実装されているが、稀に前後余計なテキストが混入するケースを考慮して復元処理を行っている（完全な耐性は保証しない）。
- 一部ファイルで記述が途中（例: pipeline._adjust_to_trading_day の続きを想定する余地あり）だが、コア機能は上記で実装済み。
- J-Quants クライアントおよび quality モジュールは外部コンポーネントとして想定され、適切な実装/モックが必要。

---

（初回リリースのため、今後のリリースでは「Changed / Fixed / Security / Deprecated / Removed」セクションに差分を追加します。）