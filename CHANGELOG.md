# Changelog

すべての重要な変更はこのファイルに記録します。本ドキュメントは Keep a Changelog の形式に準拠しています。  

現在のバージョンは 0.1.0（初回リリース）です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース — KabuSys のコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージのエントリポイント（kabusys）とバージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" と公開モジュール一覧を設定。

- 環境設定/ロード機能（kabusys.config）
  - .env および .env.local ファイルと OS 環境変数からの読み込みをサポート。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を探索）を実装。
  - export KEY=val 形式やクォート、インラインコメントなど多数の .env 書式をパース可能。
  - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /実行環境 / ログレベル等の設定値をプロパティ経由で取得・バリデーション。

- AI/NLP モジュール（kabusys.ai）
  - ニュースセンチメント分析（news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を生成して DuckDB に保存。
    - バッチサイズ、最大記事数、文字数トリム、JSON Mode を用いた堅牢なレスポンス検証、レスポンスのクリップ（±1.0）、API のリトライ（指数バックオフ）を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を明確に定義する calc_news_window を提供。
    - テスト容易性のために内部の API 呼び出し関数は差し替え可能（patch 想定）。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI を用いた JSON レスポンスのパース、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを避ける設計（date 引数依存、datetime.today()/date.today() を参照しない）。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ / 流動性（20 日 ATR、相対 ATR、平均売買代金、出来高比率）
    - バリュー（PER、ROE。raw_financials から最新財務を取得）
    - DuckDB SQL＋Python の組合せで計算し、(date, code) ベースの結果リストを返す。
  - 特徴量探索（feature_exploration）
    - 将来リターン算出（複数ホライズン対応、デフォルト [1,5,21]）
    - IC（スピアマンランク相関）計算
    - ランク化ユーティリティ（同順位は平均ランク処理）
    - ファクターの統計サマリー（count/mean/std/min/max/median）
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Data プラットフォーム機能（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間ジョブ calendar_update_job を実装。バックフィル・健全性チェックを備える。
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバック。
  - ETL パイプライン（pipeline）
    - 差分取得・保存・品質チェックのフレームワークを提供。
    - ETLResult dataclass を公開（kabusys.data.etl を経由して再エクスポート）。
    - 最終取得日のバックフィル、品質チェックの収集と報告、idempotent な保存方針を実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY に対応。API 失敗時はフェイルセーフで継続（致命的なキー未設定は例外）。

### 実装上の注意（設計上の意図・重要ポイント）
- すべての「日付を基準とする処理」はルックアヘッドバイアスを避けるため datetime.today()/date.today() の直接参照を避け、target_date 引数で制御する設計。
- DuckDB を主要な永続ストアとして利用。SQL は可能な限りウィンドウ関数等を使って効率的に実装。
- IDempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用し、失敗時は ROLLBACK を試行。ROLLBACK が失敗した場合は警告ログを出す。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密な検証を実施。サーバー系の一時エラー（5xx、接続断、タイムアウト、429）は指数バックオフでリトライ。
- テスト容易性のため、内部の API 呼び出し関数（例: _call_openai_api）は unittest.mock.patch によって差し替え可能な設計。
- .env の自動ロードはプロジェクトルート探索（.git / pyproject.toml）に依存しており、パッケージ配布後も動作するよう工夫。

### 既知の制約 / 将来の改善候補
- news_nlp の出力フォーマットやスキーマが LLM に依存するため、LLM の振る舞いに合わせた更なる堅牢化（ガードレール）が今後必要。
- 一部 DuckDB のバインド挙動（executemany の空リスト取り扱い等）への互換処理を実装しているが、DuckDB のバージョン差分に対する追加テストが望ましい。
- 現時点では strategy / execution / monitoring パッケージの公開は意図されているが、本リリースでの実装範囲は主に data / research / ai / config 周りに集中している。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。リリースノートの正確な文章化やリリース日付の調整が必要な場合は指示してください。