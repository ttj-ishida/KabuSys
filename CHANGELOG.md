# Changelog

すべての非互換性のある変更はメジャーバージョンを上げて行います。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

なお、以下の変更履歴はリポジトリのコード内容から推測して作成しています。

## [Unreleased]

- なし（初期リリース以降の未リリース変更はここに記載します）

## [0.1.0] - 2026-04-01

初回公開リリース。

### Added

- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開バージョンを `__version__ = "0.1.0"` として定義。
  - パッケージの公開 API に data, strategy, execution, monitoring を含めるようにエクスポート設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを追加。プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を優先順に読み込む。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env 解析で以下に対応：
    - `export KEY=val` 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行における行内コメントの扱い（直前がスペース/タブの場合のみコメントとみなす）
  - 環境値取得ユーティリティ `Settings` を導入し、J-Quants、kabuステーション、Slack、DBパス、監視しきい値、システム環境（env/log_level）等のプロパティを提供。必須値未設定時は ValueError を送出して誤使用を防止。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント解析モジュール `news_nlp` を実装。OpenAI（gpt-4o-mini、JSON mode）を用いて銘柄ごとにニュースを集約しセンチメントスコアを算出、`ai_scores` テーブルへ書き込む処理 `score_news` を提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり最大記事数・文字数制限、JSON レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - API の一時エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフによるリトライ実装。非リトライ対象エラーはスキップして継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch で置換可能）。
    - ニュース収集ウィンドウ計算（JST 基準→UTC 換算）を提供する `calc_news_window` 実装。
    - DuckDB に対する冪等書き込み（DELETE → INSERT）で部分失敗時に既存スコアを保護する戦略を採用。
  - 市場レジーム判定モジュール `regime_detector` を実装。ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定する `score_regime` を提供。
    - ma200 比率算出（target_date 未満のデータのみ使用してルックアヘッドを防止）、マクロニュース抽出、OpenAI 呼び出し（JSON mode）によるセンチメント評価、スコア合成、`market_regime` テーブルへの冪等書き込みを実装。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするなどフェイルセーフ設計。
    - OpenAI 呼び出しに対して再試行・エラーハンドリングを実装。

- 研究（Research）モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M）、200 日移動平均乖離（ma200_dev）、ATR ベースのボラティリティ、流動性（20 日平均売買代金・出来高比率）、Value（PER, ROE）等の算出関数を追加。
    - DuckDB 上の prices_daily / raw_financials テーブルのみを参照し本番 API にアクセスしない設計。
    - データ不足時の None 処理やログ出力を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - rank() は浮動小数点の丸め（round(v, 12)）を行い ties の扱いを安定化。
    - pandas 等の外部依存を避け、標準ライブラリ + DuckDB で実装。

- データ基盤（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定 API を追加。
    - market_calendar テーブルが未取得の場合は曜日ベースのフォールバック（週末を休場）を行う一貫した挙動。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 実行結果を表すデータクラス ETLResult を実装（品質問題やエラーメッセージの集約、辞書化メソッドを提供）。
    - 差分フェッチ、保存、品質チェックを想定したパイプライン設計に沿ったユーティリティを追加。
    - etl モジュールで ETLResult を再エクスポート。

### Changed

- （初回リリースのため該当なし）

### Fixed

- OpenAI / ネットワーク呼び出し周りの堅牢性を強化
  - JSON パース失敗や予期しない形式のレスポンスに対してログを出しつつ安全にフォールバックする処理を追加。
  - APIError の status_code の有無に依存しないエラーハンドリング、500 系はリトライ、それ以外は即座にフォールバックする方針を採用。
- DuckDB へのバルク書き込みにおける互換性対策
  - DuckDB の executemany に空リストを渡せない制約を考慮し、空チェックを行ってから executemany を実行するようにした。

### Security

- OpenAI API キーや Slack トークン、kabu API パスワード等を環境変数から取得する設計とし、必須変数未設定時に明示的に例外を投げて誤用を防止。

### Notes / Design decisions

- ルックアヘッドバイアス防止: AI やリサーチ関連の関数は datetime.today()/date.today() を直接参照せず、すべて呼び出し時に target_date を明示的に渡す設計。
- テスト容易性: OpenAI 呼び出し等外部依存部はモジュール内の関数を patch 可能にして単体テストを容易にする。
- ログ出力: 各主要処理は適切な情報ログ・警告ログを出すようになっており、運用時のトラブルシュートに配慮。

---

[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0