# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従い、セマンティックバージョニングで管理します。

なお、本リポジトリのバージョンはパッケージルートの src/kabusys/__init__.py の __version__ を参照してください。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, research, ai, execution, strategy, monitoring 等のサブパッケージを想定（__all__ に登録）。
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定 / ロード
  - 詳細な .env 読み込みロジックを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env と .env.local の読み込み順序（OS 環境 > .env.local > .env）と、OS 環境変数を保護する挙動を実装。
    - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント取り扱いなど堅牢なパーサを実装。
  - Settings クラスで各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / Paper Trading / 監視設定 / ログレベル / 環境種別など）。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。
    - Path を返す設定は expanduser を利用。

- AI（自然言語処理）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を生成。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を提供。
    - 1チャンク当たり最大銘柄数、文字数・記事数のトリム、JSON Mode レスポンスの堅牢なパース・バリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。失敗時はスキップして他銘柄に影響させないフェイルセーフ設計。
    - DuckDB への書き込みは部分置換（該当コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を確保。
    - テスト容易性のため、OpenAI 呼び出しを差し替え可能な内部関数設計（_call_openai_api を patch で置換可能）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照して ma200_ratio とマクロ記事タイトルを取得、OpenAI で macro_sentiment を算出。
    - リトライ、5xx 判定、API 失敗時のフォールバック（macro_sentiment=0.0）などフェイルセーフ実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - ルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。

- データ（Data platform）
  - ETL / パイプライン基盤（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL の実行結果・品質問題・エラー情報を格納）。
    - 差分更新・バックフィル・品質チェックを想定した設計。DuckDB を利用。
    - デフォルトのバックフィル日数等の定数を定義。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を利用した営業日判定ユーティリティ群を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがある場合は DB 値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを実装。
    - calendar_update_job を実装し、J-Quants クライアントを使った差分取得→保存（バックフィル含む）を提供。健全性チェックやログを実装。

- リサーチ / ファクター
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M）、200 日 MA 乖離、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）などの計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を積極活用し、ウィンドウ関数や LAG/LEAD による効率的な算出を実装。
    - データ不足時の None ハンドリングやログ出力を実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）、rank、factor_summary（統計サマリー）を提供。
    - horizons のバリデーション、重複除去、ランク計算での同順位処理（平均ランク）等を実装。
    - pandas 等に依存せず標準ライブラリで実装。

- その他エクスポート / モジュール構成
  - data.etl から ETLResult を再エクスポート（使い勝手向上）。
  - research パッケージから主要関数を __all__ で公開。

### Changed
- アーキテクチャ上の設計方針として各所に以下を明示
  - ルックアヘッドバイアス回避（datetime.today()/date.today() 参照回避、DB クエリは target_date 未満/排他的にするなど）。
  - API 呼び出しでのフェイルセーフ設計（失敗時はゼロやスキップで継続し、例外で全処理を止めない箇所がある）。
  - DuckDB executemany の仕様（空リスト不可）を考慮した実装。

### Fixed / Robustness improvements
- JSON レスポンスの堅牢化
  - OpenAI の JSON mode でも前後テキストが混入するケースを考慮し、最外側の { ... } を抽出してパースする復元ロジックを実装（news_nlp）。
- API エラー判定の堅牢化
  - openai SDK の APIError に対して status_code 属性の有無を安全に扱う実装。サーバー側 5xx はリトライ対象、それ以外はスキップする方針を明示。
- DuckDB 書き込みの冪等性と部分失敗耐性
  - ai_scores / market_regime への書き込みは該当コードのみ DELETE → INSERT で行い、部分失敗時に他のコードを保持するように設計。
- .env パーサの改善
  - export キーワード対応、クォート内エスケープ、インラインコメント扱いの改善、キー空白検出の強化など。

### Documentation / Comments
- 各モジュールに詳細なドキュメントコメントを追加（処理フロー、設計方針、失敗時のフェイルセーフ挙動、テスト差し替えポイント等）。
- AI モジュールや ETL モジュールにおいてテストや運用を容易にする注意点（API キー注入可能、環境変数による動作制御など）を明示。

---

今後の予定（想定）
- 単体テスト・統合テストの追加（OpenAI 呼び出しのモック等）
- jquants_client の実装・テスト（本コードでは参照されるが実体は別モジュールとして実装想定）
- 実行・監視（execution / monitoring）モジュールの具現化（発注・監視ロジック）
- ドキュメント整備（設計書、運用手順、デプロイ手順など）

もしリリース日や変更内容の表現を特定日付に合わせたい、あるいは追加で「破壊的変更」「互換性の注意点」などのセクションを加えたい場合は指示してください。