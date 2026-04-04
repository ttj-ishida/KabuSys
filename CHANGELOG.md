# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの最初の公開バージョンとして 0.1.0 をリリースしました。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04

### Added
- パッケージの初期リリース。モジュール構成（主要 public パッケージ）:
  - kabusys.data, kabusys.research, kabusys.ai, kabusys.config, kabusys.research, kabusys.__init__（バージョン情報 __version__ = 0.1.0 を含む）

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動的に読み込む仕組みを実装。
  - プロジェクトルート探索: __file__ を起点に親ディレクトリに .git または pyproject.toml を探してルートを特定（CWD 非依存）。
  - .env パーサーの強化:
    - 空行・コメント行（#）を無視。
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォート無し値のインラインコメント処理（直前が空白/タブの場合のみコメントとみなす）。
  - 自動読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
  - OS 環境変数を保護する protected 機能（.env 上書き時に既存 OS 環境変数を上書きしない）。
  - 自動読み込みの無効化オプション: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードをスキップ可能。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB/SQLite）/監視設定などの既定値と取得メソッド。
    - 必須値は _require() で検出され、未設定時は ValueError を発生させる。
    - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL（DEBUG/INFO/...）の検証、ユーティリティプロパティ（is_live 等）。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini の Chat Completions + JSON mode）へバッチ送信してセンチメントスコアを生成。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大 10 記事、最大文字数 3000 文字でトリム。
    - 再試行（リトライ）方針: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（デフォルト上限あり）。
    - レスポンス検証と復元処理: JSON パース、"results" の存在確認、各要素の型チェック、未知コードは無視、スコアを ±1 にクリップ。
    - DB 書き込みは冪等的（DELETE → INSERT）で、部分失敗時に既存の他銘柄スコアを保護。
    - API 呼び出し部分は _call_openai_api に抽象化され、テスト時に差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用し、ルックアヘッドを防止。
    - マクロニュース: raw_news からマクロキーワードでフィルタし、OpenAI でセンチメント評価（記事がない場合は LLM 呼び出しなし）。
    - フェイルセーフ: API 失敗時やパース失敗時は macro_sentiment = 0.0 にフォールバック（例外を上げず継続）。
    - レジームスコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）で、テスト用に差し替え可能。

- Data（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータが無い場合は曜日ベース（日曜/土曜は非営業日）でフォールバック。
    - next/prev/get_trading_days は DB 登録値を優先しつつ未登録日は曜日フォールバックで補完、一貫した結果を返す設計。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants API 経由で差分取得 → 保存）。バックフィルと健全性チェック（将来日付の異常検出）を備える。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得・保存・品質チェックのフレームワーク（jquants_client と quality モジュールを利用する想定）。
    - デフォルトのバックフィル日数やカレンダー先読み等の定義を含む。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）。データ不足時は None を返すロジック。
    - Volatility / Liquidity: 20 日 ATR（true range の扱いを明確化）、ATR の相対値（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: raw_financials から最新の EPS/ROE を取得し PER / ROE を計算（EPS が 0/欠損 の場合は None）。
    - いずれも DuckDB 上の SQL ウィンドウ関数で実装し、戻り値は (date, code) を含む dict のリストとして返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）までのリターンを一括 SQL で取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（ties は平均ランクで処理）。有効レコードが 3 件未満の場合は None を返す。
    - ランキングユーティリティ（rank）および統計サマリー（factor_summary）を実装。
  - research パッケージは有用な関数を __all__ で公開。

### Changed
- 初版のため該当なし（初期実装）。

### Fixed
- 初版のため該当なし。

### Security
- 初版のため該当なし。

Notes:
- 全体設計で共通の方針として「ルックアヘッドバイアスを発生させない」「API 失敗時はサービスを停止させずフェイルセーフにフォールバックする」「DuckDB に対する互換性（executemany の空リスト問題等）に配慮する」等を採用しています。
- OpenAI 連携部はテスト容易性のため呼び出しを抽象化しており、ユニットテスト時に差し替え可能です。
- このリリースは「機能的な初期実装」を提供します。今後、API クライアント実装（jquants_client 等）、監視・実行ロジック、ドキュメントや追加ユニットテストの拡充を予定しています。