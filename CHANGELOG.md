# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新リリース
------------

### [Unreleased]

- 今後の変更点をここに記載します。

安定版
-----

### [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能と実装方針を含みます。

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開 API を __all__ で整理（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。
  - .env パーサ実装：export プレフィックス対応、クォート内エスケープ対応、インラインコメントの取り扱い、無効行スキップ等。
  - 自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境モード / ログレベルなどの取得メソッドを実装。
  - 環境値検証：KABUSYS_ENV, LOG_LEVEL の許容値チェック、必須変数未設定時は明確なエラーメッセージ（_require）。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news を元に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント ai_score を算出し ai_scores テーブルへ保存する処理を実装。
  - JST ベースのニュースウィンドウ計算 calc_news_window を実装（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
  - 記事集約ロジック（_fetch_articles）：銘柄ごとに最新 N 件・文字数トリム対応。
  - バッチ送信（最大 20 銘柄／回）、レスポンス検証（JSON 抽出・構造チェック・スコア数値検証）、スコアの ±1.0 クリップ。
  - ネットワークエラー / レート制限 / 5xx に対する指数バックオフリトライを実装。非再試行エラーはスキップ（フェイルセーフ）。
  - DuckDB 向けの安全な書き込みロジック（対象コードのみ DELETE → INSERT）と executemany の空リスト回避。
  - テスト容易性を考慮し、OpenAI 呼び出し箇所を差し替え可能（関数パッチ化を前提）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込みする実装を追加。
  - prices_daily と raw_news を参照して ma200_ratio を計算・マクロニュース抽出し、OpenAI により macro_sentiment を算出（最大記事数制限）。
  - スコア合成、閾値に基づくラベル付け（bull / neutral / bear）を実装。
  - OpenAI 呼び出しのリトライ・バックオフ、API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試みて例外を伝播。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベースのフォールバック（週末除外）。DB 登録値優先の一貫した挙動。
    - カレンダー夜間更新ジョブ calendar_update_job：J-Quants クライアントから差分取得して save する処理（バックフィルと健全性チェック含む）。
    - 最大探索日数やバックフィル幅などの安全パラメータを定義し無限ループや異常値を防止。

  - ETL パイプライン（pipeline）
    - ETLResult データクラスを追加し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約可能に。
    - 差分更新・バックフィル方針、品質チェックの扱い（重大度は収集され呼び出し元が判断）など設計を文書化。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

  - etl モジュールで ETLResult を公開。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR, 相対 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を DuckDB を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、SQL ウィンドウ関数を活用した効率的な取得。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）、IC（スピアマン ρ）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存なしで純標準ライブラリ + DuckDB により実装。

Changed
- 設計上の方針を明記（各モジュール共通）
  - ルックアヘッドバイアス防止のため date.today()/datetime.today() をスコープ内で直接参照しない設計。
  - OpenAI/API 呼び出しは失敗しても全体を停止させない（フェイルセーフ）方針。
  - DuckDB 固有の挙動（executemany の空パラメータ不可等）を考慮した実装。

Fixed
- （初回リリースのため既存バグ修正は該当なし。実装中に考慮した互換性処理やフォールバックロジックを含む。）

Security
- 機密設定（API キー等）は Settings 経由で明示的に要求し、未設定時は ValueError を送出して誤動作を防止。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）で受け取る前提。
- テスト容易性のため OpenAI 呼び出し箇所は関数単位で差し替え／モック可能に実装。
- DuckDB を主要なオンディスク分析エンジンとして想定。SQL 内での NULL 扱いやウィンドウ関数の使い方は互換性を考慮して記述。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT 等）実装し、部分失敗時の既存データ保護を行う。

Acknowledgements
- このリリースは初期実装（プロトタイプ〜初期運用向け）を目的としており、今後の改善でパフォーマンス最適化、エラーハンドリングの強化、Operator エクスポーズ（CLI / API）等を予定しています。

---
[0.1.0]: # (初回リリース)