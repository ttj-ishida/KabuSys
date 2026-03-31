# Changelog

すべての変更は Keep a Changelog の慣例に従って記載します。  
このファイルはリポジトリのコードから推測して作成した初期リリースの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Known issues / TODO
- data.pipeline._get_max_date 関数の末尾に不完全な記述（`return date.fro` のようなタイポ）があり、実行時エラーの原因になる可能性があります。修正が必要です。
- パッケージのトップで __all__ に含まれる "execution", "strategy", "monitoring" モジュールは参照されているものの、今回提供されたソースには該当実装が含まれていません。これらは今後実装または補完が必要です。

---

## [0.1.0] - 2026-03-31

初回公開（推測） — 基本的なデータ取得/ETL、研究用ファクター計算、ニュース/NLP、レジーム検出等のコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。
  - パッケージ API として "data", "strategy", "execution", "monitoring" をエクスポート（将来的に実装されるモジュールを想定）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル または環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートはモジュール位置から `.git` または `pyproject.toml` を探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパースは以下をサポート / 考慮:
    - `export KEY=val` 形式
    - シングル/ダブルクォート付き値（バックスラッシュエスケープを考慮）
    - コメントの扱い（クォート内は無視、クォート外はインラインコメントを判定）
  - Settings クラスを提供し、アプリ全体の設定値（J-Quants、kabu API、Slack、DBパス、監視閾値、環境名、ログレベル等）をプロパティ経由で取得可能。必須値は未設定時に ValueError を送出。
  - env / log_level のバリデーション（許容値セット）を実装。

- AI: ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。
  - 機能のポイント:
    - タイムウィンドウ計算（JST基準 → UTC naive datetime に変換）: calc_news_window。
    - 銘柄ごとに最新記事をトリム（1銘柄あたり最大記事数・文字数を制限）。
    - 最大バッチサイズ（_BATCH_SIZE=20）で分割して API コール。
    - レートリミット/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装（_MAX_RETRIES）。
    - レスポンスの厳密な JSON 期待（ただし前後ノイズの復元ロジックあり）とバリデーション（結果構造・スコア型など）。
    - スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT（冪等性）を確保。DuckDB executemany の空リスト注意点に対応。
    - テスト容易性: OpenAI 呼び出しを包む _call_openai_api をパッチ差し替え可能。

- AI: 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（Nikkei225 連動ETF）200日移動平均乖離とマクロニュース LLM センチメントを合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する処理を実装。
  - 処理概要:
    - ma200_ratio（最新終値 / 200日単純移動平均）計算（ルックアヘッド回避のため target_date 未満のデータのみ使用）。
    - マクロキーワードでフィルタした raw_news タイトルを抽出（最大 _MAX_MACRO_ARTICLES 件）。
    - OpenAI にマクロニュースを投げてセンチメントを取得（失敗時は 0.0 にフォールバック）。
    - 重み付け（70%: MA 指標、30%: マクロセンチメント）でスコアを合成しラベル決定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等に実行。失敗時は ROLLBACK を試行。
  - フェイルセーフ設計: API 失敗や JSON パース失敗時に例外を投げずに中立値を使用する実装。

- Research（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を SQL ウィンドウ関数で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。price と組み合わせて出力。
    - 各関数は同一インターフェース（DuckDB 接続 + target_date）で (date, code) をキーとする dict リストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（IC）をランク付けして計算。有効レコードが少ない場合は None を返す。
    - rank: 同順位は平均ランク（ties の平均化）。丸めで ties 判定の安定化を実施。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

- Data（src/kabusys/data/*）
  - calendar_management:
    - JPX カレンダーの管理ロジック（market_calendar テーブル）と夜間バッチ更新 job（calendar_update_job）を実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない日については曜日ベース（土日非営業）でのフォールバックを実装し、DB がまばらな場合でも一貫した判定を行うよう設計。
    - 更新ジョブはバックフィル（直近 _BACKFILL_DAYS を再取得）と健全性チェック（未来日付の異常検出）を備える。
    - J-Quants 用クライアント呼び出し点を抽象化（jquants_client モジュールに依存）。
  - pipeline / ETL:
    - ETLResult データクラスで ETL 実行結果（取得/保存件数、品質問題、エラー等）を集約。to_dict で品質問題を辞書化して出力可能。
    - pipeline モジュールは差分取得、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を組み合わせる設計方針を実装するための基礎を提供。
    - ETL の設計では backfill による後出し修正吸収、品質チェックは収集して呼び出し元が対処する方針（Fail-Fast ではない）を採用。
    - data.etl で ETLResult を再エクスポート。

- 実装上の設計方針（全体）
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today()/date.today() を直接参照せず、target_date を外部から渡す設計。
  - DuckDB をデータストアとして想定。SQL と Python の組合せで計算を行う。
  - OpenAI API 呼び出しには冪等性・フォールバック・リトライを考慮した実装。
  - DB 書き込みは可能な限り冪等に（DELETE → INSERT 等）行い、部分失敗時に既存データを不要に削除しない配慮あり。
  - テスト容易性を考慮し、OpenAI 呼び出しを差し替え可能にするなどの hook を提供。

### Changed
- N/A（初回リリースのため変更履歴なし）

### Fixed
- N/A（初回リリースのため修正履歴なし）

### Removed
- N/A

### Security
- 本リリースは外部 API キー（OPENAI_API_KEY 等）を環境変数から取得するため、運用時は機密管理（Vault / 環境変数の保護等）を推奨。

---

補足ノート（運用時の注意）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID のようなキーを Settings が必須としているため、未設定時は ValueError が発生します。
- 自動 .env ロードを無効化したいテストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- OpenAI 呼び出しのフォールバック挙動:
  - news_nlp / regime_detector ともに API エラー時は基本的にスキップまたは中立スコア（0.0）にフォールバックする設計です（致命的な例外を上げない）。
- DuckDB の executemany は空リストを受け付けない制約があるため、実装は空チェックを行ってから executemany を呼び出します。
- 一部コード（data.pipeline._get_max_date）に不備が見られるため、本番投入前に該当箇所の修正・テストを行ってください。

以上。必要であれば各機能ごとにより詳しい変更内容（関数一覧、公開 API、呼び出し例、マイグレーション手順など）を追記します。どのレベルの詳細が必要か教えてください。