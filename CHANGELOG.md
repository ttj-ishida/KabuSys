# CHANGELOG

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

履歴はコードベースから推測して作成しています。実際のリリースノートや日付は適宜調整してください。

## [Unreleased]
- （現在の開発中の変更点はここに記載）

## [0.1.0] - 2026-03-28
初回リリース（推定）。以下の主要機能・設計方針が実装されています。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加: バージョン `0.1.0`（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を起点に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト用）。
    - .env のパースは `export KEY=value` 形式、クォート（シングル/ダブル、エスケープ）およびコメントを扱える堅牢実装。
    - .env 読み込み時の上書き制御（protected set により OS 環境変数の保護）。
  - 必須環境変数チェックを実装（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。
  - 各種設定プロパティを提供（KABU API base URL、DuckDB/SQLite データパス、環境・ログレベルの検証など）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。

- AI（NLP）モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理単位は最大 20 銘柄（_BATCH_SIZE）。
    - 各銘柄は最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI JSON Mode を利用、レスポンスをバリデーションしてスコアを ±1.0 にクリップ。
    - 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - スコア書き込みは部分的な失敗に備え idempotent（DELETE → INSERT）で実施。DuckDB の executemany 空リスト制約に配慮。
    - ニュース時間ウィンドウは JST 基準（前日 15:00 〜 当日 08:30）を UTC に変換して扱う。
  - 市場レジーム判定（score_regime）
    - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる記事抽出、OpenAI 評価（gpt-4o-mini）、重み付き合成、閾値判定（BULL/BEAR 0.2）を実装。
    - API 失敗時は macro_sentiment = 0.0 のフェイルセーフ。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実施。エラー時は ROLLBACK を試みて上位へ例外伝播。

- Research（研究用分析）モジュール（src/kabusys/research）
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA 乖離率）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日の株価から PER/ROE を計算（EPS が 0/欠損の際は None）。PBR・配当利回りは未実装。
    - すべて DuckDB を直接参照し、外部 API にはアクセスしない設計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証（正の整数かつ <= 252）。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を計算、十分なサンプルがなければ None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を集計。
    - rank: 同順位は平均ランクを返す実装。浮動小数丸め対策あり。
  - research パッケージは便利関数を再エクスポートしている。

- Data（データプラットフォーム）モジュール（src/kabusys/data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先、未登録日は曜日ベースでフォールバック。最大探索範囲で無限ループを回避。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得 → 保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開して ETL 実行結果を体系的に扱う。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）設計を想定したユーティリティ実装。
    - DuckDB のテーブル存在チェック、最大日付取得などの内部ユーティリティを提供。
  - jquants_client と quality との連携を想定（外部クライアントは別モジュール）。

### 変更 (Changed)
- （初回リリースのため変更履歴はなし。実装上の設計決定を記載）
  - 設計方針: ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() の直接参照を避け、関数引数として target_date を受け取る設計。
  - DuckDB を主要データストアとして利用し、SQL と Python ロジックを組合せて分析処理を実装。
  - OpenAI 呼び出しは各モジュール内で独立実装。テスト時に差し替え可能（unittest.mock.patch を想定）。

### 修正 (Fixed)
- （初回リリースのためバグ修正履歴はなし）
- 実装上の堅牢性対策（推定実装）:
  - .env 読み込みでファイルアクセス失敗時に警告を出す。
  - OpenAI 応答の JSON パースが失敗した場合に前後のテキストから {} を抽出して復元を試みるフォールバックを実装。
  - API 呼び出し失敗時に適切にログとフェイルセーフ（0.0 やスキップ）を行う実装。

### 既知の制約 / TODO（コードからの推測）
- PBR・配当利回り等の一部バリューファクターは未実装（calc_value の備考）。
- news_nlp モジュールは OpenAI の JSON モードを前提とするが、LLM 出力のばらつきに備えたパース回復ロジックを実装しているものの、完全な健全性保証は要検討。
- ETL の実際の J-Quants クライアント実装（jquants_client）と品質検査（quality）は別モジュールであり、環境依存のため運用時の設定が必要。
- OpenAI API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。キー設定がない場合は ValueError を送出。

---

注: 本 CHANGELOG は提示されたソースコードの内容から機能・設計を推測して作成しています。実際のリリースノートや日付、ユーザー向けの変更点説明は、プロジェクト実情に合わせて調整してください。