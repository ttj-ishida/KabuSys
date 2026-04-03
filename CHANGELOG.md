# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、意図的に後方互換や設計上の判断を記録しています。

なお、本ファイルはコードベース（src/kabusys 以下）の現在の実装内容から推測して作成しています。実際のコミット履歴ではなく、実装された機能・設計方針・既知の動作に基づく要約です。

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

初回公開リリース。本バージョンでは日本株自動売買システムのコアライブラリ群を実装・公開しています。主な追加点と設計上の留意点を以下に示します。

### Added
- 全体
  - パッケージ kabusys の初期リリース。公開 API として data, research, ai, monitoring 等のサブパッケージを想定する __all__ を定義。
  - バージョン番号を `__version__ = "0.1.0"` として設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を基準）。
  - 読み込みの優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントルールに対応）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / LINE API / DB パス / 監視設定 / システム設定（環境・ログレベル判定）などのプロパティを提供。未設定必須キーは明示的にエラーを投げる。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- AI（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を結合し、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini の JSON mode）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する calc_news_window を実装。
    - チャンク処理（1 API コールあたり最大 20 銘柄）、記事数・文字数上限（銘柄あたり最大 10 件、3000 文字）でプロンプト肥大化を制御。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフリトライを実装。その他のエラーはスキップして処理継続（フェイルセーフ）。
    - OpenAI レスポンスの堅牢なバリデーションと JSON 復元処理（前後余計テキストの抽出）を実装。スコアは ±1.0 にクリップ。
    - DuckDB の executemany の制約を考慮し、空パラメータを回避する実装（部分置換方式: DELETE → INSERT）。
    - テスト向けフックとして _call_openai_api を patch 可能に実装。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の market_regime テーブルへ書き込む機能を実装。
    - prices_daily からの MA 計算は target_date 未満のみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事の抽出はキーワードベース（日本・米国系の主要語句）で行い、記事が無い場合は LLM 呼び出しをスキップして macro_sentiment = 0.0 を採用（フェイルセーフ）。
    - OpenAI 呼び出しに対してリトライ（エクスポネンシャルバックオフ）を行い、最終的に失敗した場合は 0.0 にフォールバック。レスポンス JSON パース失敗時も 0.0 にフォールバック。
    - 計算結果は冪等に market_regime テーブルへ書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データ（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを J-Quants から差分取得して market_calendar テーブルを更新する夜間ジョブ calendar_update_job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。DB のデータが存在しない場合は曜日ベースのフォールバック（週末除外）を採用。
    - DB が部分的にしかない場合でも一貫した挙動となるように設計（DB 値優先、未登録は曜日フォールバック）。
    - 最大探索日数やバックフィル・健全性チェック（将来日付の異常検出）を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー等を格納）。
    - ETL の設計方針（差分更新、backfill による後出し修正吸収、品質チェックは収集して呼び出し元に委ねる）を反映。

- Research（src/kabusys/research）
  - ファクター計算・特徴量探索モジュールを実装。
    - factor_research.py: モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）等の計算関数（calc_momentum, calc_volatility, calc_value）。
    - feature_exploration.py: 将来リターン算出（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、rank, factor_summary 等のユーティリティ。
  - 外部依存（pandas 等）を排除し、DuckDB と標準ライブラリのみで動作するよう実装。

- その他
  - 一部モジュールで logging を適切に利用し、処理の状況とフェイルセーフ挙動を記録。
  - テスト容易性を考慮した設計（API 呼び出し部分の差し替え可能化、環境ロードの無効化フラグなど）。

### Changed
- （初回リリースのため適用なし）

### Fixed
- （初回リリースのため適用なし）

### Removed
- （初回リリースのため適用なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。これにより既存の OS 環境変数が .env によって不用意に上書きされないよう制御。

### Notes / Design decisions / Known behaviors
- ルックアヘッドバイアス対策: 各種処理（AI スコア、レジーム判定、ファクター計算）は内部で date.today()/datetime.today() を直接参照せず、外部から target_date を受け取る設計。
- OpenAI 呼び出しのレスポンスは JSON mode を利用するが、実世界では余計な前後テキストが混入することがあるため、復元ロジックを実装している。
- API 呼び出し失敗時は基本的にフェイルセーフで継続し、最終的にはスコアを 0.0 にフォールバック（重大障害以外は例外を上げず処理を継続）。
- DuckDB のバージョン差異（executemany の空リスト不可、配列バインドの不安定性等）に対して互換性を持たせる実装を行っている。
- .env パーサは一般的なケース（export、クォート、エスケープ、コメント）に対応するが、特殊なケースは未検証の可能性あり。

もし特定モジュールごと、あるいはリリース履歴に沿ったより細かい記述（コミット単位や開発履歴の推定）を希望される場合は、その旨をお知らせください。