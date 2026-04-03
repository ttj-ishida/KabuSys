# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトのバージョニングは semver を使用します。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを公開。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン（0.1.0）および公開モジュールを定義。

- 環境設定 / .env ローダー
  - src/kabusys/config.py
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env 行パーサを実装（`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応）。
    - 読み込み時の override/protected 制御をサポートし、OS 環境変数の保護を実現。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定を環境変数から取得するプロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値外は ValueError）。
    - ファイルパス系設定は Path オブジェクトで返す（expanduser 対応）。
    - 監視用フラグや閾値（CPU/MEM/DISK 等）の型変換とデフォルト値を提供。

- AI モジュール（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を取りまとめて銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) の JSON Mode にバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（UTC で前日 06:00 ～ 23:30）を使用。calc_news_window 関数を提供。
    - 1 銘柄あたり最大記事数 / 最大文字数でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - バッチサイズ制御（1 API コールあたり最大 20 銘柄）。
    - API 呼び出し失敗（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフリトライ実装。その他のエラーはスキップして継続するフェイルセーフ挙動。
    - レスポンスの厳密なバリデーション（JSON 抽出・results キー・各要素の code/score 検証、スコアの数値化と ±1.0 クリップ）。不正応答はスキップして他銘柄を保護。
    - DuckDB への書き込みは idempotent（対象コードを先に DELETE → INSERT）で、部分失敗時に他コードの既存スコアを消さない実装（executemany の空リスト扱いへの対応あり）。
    - テスト容易性のため _call_openai_api を分離し patch で差し替え可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - MA の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事はニュース NLP と同様に記事抽出を行い、OpenAI に JSON 出力を要求して macro_sentiment を取得。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0。
    - LLM 呼び出しはリトライ / backoff を実装し、最終的に失敗した場合は macro_sentiment=0.0 でフェイルセーフ。
    - スコア合成後に market_regime テーブルへ冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込み。エラー発生時は ROLLBACK を試みて上位へ例外を伝搬。
    - 各所にログ出力を実装（WARN/INFO）。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（true range を正しく扱う）、相対 ATR（atr_pct）、20 日平均売買代金、出来高変化率を計算。必要行数未満は None を返す。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER/ROE を計算。EPS が 0 または欠損時は PER を None にする。
    - いずれも DuckDB（prices_daily / raw_financials）を利用、外部 API にはアクセスしない設計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の入力検証を実施。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。有効レコード 3 件未満は None。
    - rank: 同順位は平均ランクとするランク付けを実装（丸め誤差対策で round を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Data（ETL・カレンダー管理・ユーティリティ）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）を実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にカレンダーがない場合は曜日（平日=営業日）でフォールバックする一貫した挙動を提供。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ（バックフィル、健全性チェック、保存は jq.save_market_calendar を利用して冪等保存）。
    - 探索の最大上限や過剰な未来日付に対する保護ロジックを実装。

  - src/kabusys/data/pipeline.py / etl.py
    - ETLResult データクラス（pipeline.ETLResult を data.etl で再エクスポート）。
    - ETL の設計方針や DB 差分取得、バックフィル、品質チェック（quality モジュール連携）に基づく実装方針を定義。
    - ETLResult は処理結果の集約、品質問題の集計、辞書変換ユーティリティ（to_dict）を提供。
    - DuckDB のテーブル存在チェックや最大日付取得用ユーティリティを実装（互換性考慮）。

- モジュール公開の整理
  - ai、research、data パッケージの __init__.py による主要関数・ユーティリティの再エクスポートを整備（例: kabusys.ai.score_news / score_regime、kabusys.research.* 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を参照。キー未設定時は明示的に ValueError を送出して誤動作を防止。

### Notes / Implementation details / フェイルセーフ
- ルックアヘッドバイアスを避けるため、全モジュールで datetime.today() / date.today() を直接基準に用いない設計。関数は target_date を引数として扱う。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なパースを行う。パース失敗や API エラー発生時は最終的に安全なデフォルト（例: macro_sentiment=0.0、スコア取得スキップ）で処理継続。
- DuckDB への書き込みは可能な限り冪等に実装（DELETE → INSERT の順）し、部分失敗が既存データを破壊しない工夫を行っている。
- ロギングを多用して異常検知を容易にし、ROLLBACK に失敗した場合のログ出力など冗長性のあるエラーハンドリングを実装。

---

作成した CHANGELOG はコードベースの公開された実装仕様に基づいて推測した内容を含みます。実際のリリースノートに含める場合は、デプロイ日・責任者・追加で伝えたい運用上の注意点などを追記してください。