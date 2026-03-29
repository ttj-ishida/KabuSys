Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。パッケージのバージョン情報（__version__ = "0.1.0"）を基に 0.1.0 を初版リリースとして記載し、実装内容から推測される追加機能・設計方針・既知の挙動をまとめています。

CHANGELOG.md
=============

全般
----
このプロジェクトは Keep a Changelog のフォーマットに従って変更履歴を管理します。  
安定したリリースはセマンティックバージョニングに従います。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------
- （現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------
最初の公開リリース。

Added
- パッケージ初期構成
  - kabusys パッケージを追加。公開 API として data, research, ai, config などのサブパッケージをエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定をロードする Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込み。
    - OS 環境変数を保護（読み込み時に既存の環境変数を上書きしない、.env.local は上書き可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env のパースを堅牢化:
    - export KEY=val 形式の対応、クォート文字列中のバックスラッシュエスケープ対応、行末コメントの取り扱い等。
  - 必須値取得用のヘルパー _require と各種プロパティ（J-Quants, kabu API, Slack, DB パス, 環境・ログレベル判定等）。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を対象にニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄毎のセンチメント ai_score を計算。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数・文字数上限でトリム。
    - API 呼び出しに対するリトライ（429, ネットワーク, タイムアウト, 5xx）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score 検証）とスコアのクリップ。
    - DB 書き込みは部分置換（該当 code に対して DELETE → INSERT）で冪等性と部分失敗時の既存データ保護を確保。
    - OpenAI 呼び出し箇所はテスト差し替え用に _call_openai_api を分離。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（N225 連動型）の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - prices_daily から過去データのみを参照し、ルックアヘッドバイアスを回避する設計。
    - マクロニュース抽出はキーワードベースで最大 20 記事を抽出し、OpenAI に JSON 出力を要求。
    - API エラー時はフェイルセーフで macro_sentiment = 0.0 にフォールバック。
    - DB 書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK で復旧。

- データ処理（kabusys.data）
  - DuckDB を用いた ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得数・保存数・品質検査結果・エラー一覧などを保持）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント経由のデータ取得を想定）。
    - テーブル存在チェック・最大日付取得ユーティリティを提供。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX の市場カレンダー（market_calendar）を扱うユーティリティ群を実装。
    - 営業日判定関数: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job: J-Quants から差分取得し market_calendar を冪等に更新（バックフィルと健全性チェックを実装）。
    - DB 登録がない場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - 最大探索日数 _MAX_SEARCH_DAYS による無限ループ防止。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算するユーティリティを実装。
    - データ不足時には None を返すことで安全に扱える設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、最大 252 営業日チェック）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）とランク化ユーティリティ rank。
    - factor_summary による基本統計量（count/mean/std/min/max/median）出力。
    - pandas 等外部依存なしで標準ライブラリと DuckDB のみで完結。

Changed
- （初回リリースのため過去の変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- OpenAI API キーや各種シークレットは環境変数経由で取得する設計。  
- .env 自動読み込み時に OS 環境変数は保護され、.env.local は上書き可能。

Design / 動作上の注意（既知の挙動）
- ルックアヘッドバイアス対策:
  - 日付参照に datetime.today() / date.today() を直接用いない方針。各関数は target_date を明示的に受け取る。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用し JSON mode（response_format）で厳密な JSON を要求。API 失敗時はフェイルセーフ（0.0 やスキップ）で進行する挙動。
  - テスト容易性のため _call_openai_api を patch して差し替え可能。
- DuckDB 依存:
  - 全データ操作は DuckDB 接続を受け取る設計。executemany に空リストを与えない等の互換性考慮あり（DuckDB 0.10 に対する対処）。
- DB 書き込みの冪等性:
  - ai_scores / market_regime / market_calendar などの更新は DELETE → INSERT、または ON CONFLICT 相当の保存で冪等性を維持。
- 必須環境変数:
  - OpenAI API キー、J-Quants リフレッシュトークン、Slack 等の必須変数は未設定時に ValueError を投げる設計（呼び出し側でハンドルする必要あり）。
- データ不足時のデフォルト:
  - ma200 関連やニュースが不足する場合、明示的に中立値（1.0 や 0.0）を返して処理継続する。

Breaking Changes
- なし（初回リリース）

著作・ライセンス
- リポジトリ内の LICENSE を参照してください（この CHANGELOG はコードベースから推測して作成したものです）。

補足
- この CHANGELOG は提供されたソースコードからの実装内容を推測して作成しています。実際の公開リリースにあたっては README、リリースノート、パッケージのメタ情報と合わせて調整してください。