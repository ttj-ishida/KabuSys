Keep a Changelog
=================
すべての重要な変更を日付順で記録します。  
このファイルは「Keep a Changelog」形式に従っています。

リリース方針
-----------
- メジャー/マイナー/パッチのセマンティックバージョニングに準拠します。
- 各リリースは「Added / Changed / Fixed / Deprecated / Removed / Security」ブロックで記載します。

[0.1.0] - 2026-03-29
--------------------
初回公開リリース。kabusys のコアコンポーネントと主要機能群を実装しました。

Added
- 基本パッケージとバージョン
  - パッケージ名: kabusys、バージョン 0.1.0 を実装。
  - パッケージトップは __all__ で data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWDに依存しない実装。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env 解析は以下の挙動に対応:
    - コメント行・空行の無視、export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い（クォート無しは "#" の直前が空白/タブならコメント扱い）。
    - ファイル読み込み失敗時に警告を出力。
    - 既存 OS 環境変数を保護する protected セットの概念。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム設定（env, log_level, is_live 等）用プロパティを実装。
    - 必須環境変数未設定時は _require() により ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の許容値をバリデーション。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄ごとに gpt-4o-mini を使ってセンチメントを -1.0〜1.0 に評価。
    - タイムウィンドウは target_date に対して前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を対象とする calc_news_window 実装。
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最大 10 記事・3000 文字までトリム。
    - API 呼び出しは JSON Mode を利用。レスポンスのバリデーションとスコアのクリップ（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。
    - 書き込みはトランザクションで ai_scores テーブルに対して「対象コードのみ」DELETE → INSERT を行い、部分失敗時に既存データを保護。
    - テストのために _call_openai_api をモック差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次でレジーム判定（bull/neutral/bear）。
    - prices_daily から MA200 乖離を計算し、raw_news からマクロキーワードで記事抽出。
    - OpenAI（gpt-4o-mini）を用いた macro_sentiment を取得、API 失敗時はフェイルセーフで macro_sentiment = 0.0 を使用。
    - レジームスコア合成・閾値評価および market_regime への冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しのリトライ制御、JSON レスポンスパースの堅牢化を実装。
    - モジュール間の結合を避けるため、news_nlp の内部関数は再利用せず独自実装。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを利用した営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバック。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - calendar_update_job を実装し、J-Quants API から差分取得・バックフィル・冪等保存を行う（jquants_client を利用）。
    - 健全性チェック（最終取得日が極端に未来ならスキップ）とログ出力を実装。
  - ETL パイプラインユーティリティ (kabusys.data.pipeline, etl)
    - ETLResult データクラスを公開（etl では ETLResult を再エクスポート）。
    - 差分更新、バックフィル、保存（jquants_client の save_* を想定）、品質チェック（quality モジュールとの連携）を想定した設計。
    - テーブル存在チェック、最大日付取得ユーティリティを実装。
    - ETLResult は品質問題とエラー情報を集約し、辞書化する to_dict を提供。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity: 20 日 ATR, ATR/price, 20 日平均売買代金, 出来高比を計算する calc_volatility。
    - Value: raw_financials と当日の価格から PER, ROE を計算する calc_value（EPS が 0/NULL の場合は None）。
    - DuckDB を利用した SQL 主導の実装。データ不足時に None を返す挙動。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - Information Coefficient（Spearman の ρ）計算 calc_ic（最小有効レコード数チェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランクを割当）。
    - カラム統計サマリ factor_summary（count/mean/std/min/max/median）を提供。
  - research パッケージは主要関数を __all__ で再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示的に失敗するため、意図しないキー漏洩を防ぐ設計。

注意事項 / 既知の制約
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）のため、空チェックを行ってから executemany を呼ぶ実装にしてあります。
- LLM レスポンスの厳密さ:
  - gpt-4o-mini を JSON Mode で使用する設計だが、実際のレスポンスに前後余計なテキストが混ざる可能性を考慮し、JSON 抽出処理を実装しています。必ずしも完璧でないため、LLM 出力フォーマットの安定化が推奨されます。
- フェイルセーフ設計:
  - AI API の失敗時は例外を投げず（多くのケースで）0.0 を使用して継続する実装になっており、ETL やスコア集計の「継続性」を優先しています。運用でのアラートやモニタリング設定を推奨します。
- タイムゾーン:
  - ニュースウィンドウ等は内部で UTC naive datetime を使用し、target_date を基準に JST→UTC 変換相当の計算を行っています。DB の日時カラムは UTC 前提で扱う想定です。
- テスト支援:
  - OpenAI 呼び出し用の内部ラッパー関数（_call_openai_api）はユニットテスト時に patch して差し替え可能です。
- 外部依存:
  - pandas 等を使用せず、標準ライブラリ + duckdb + openai ライブラリでの実装を意図しています。

将来の改善案（非包括的）
- 更なるエラーメトリクスとモニタリング（Slack 通知やメトリクス出力）。
- OpenAI レスポンスのスキーマ検証を強化するための JSON スキーマ導入。
- ETL の差分取得ロジックの追加実装（現状は補助ユーティリティを提供）。
- 複数モデル・モデル切替の抽象化、モデルごとのレート制御。

クレジット
- 実装は DuckDB と OpenAI API に依存します。jquants_client / quality モジュールは外部または別モジュールとして連携する想定です。

---- END OF CHANGELOG ----