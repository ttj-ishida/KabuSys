CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
ルール: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （なし）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース。
  - src/kabusys/__init__.py に __version__ = "0.1.0" を定義し、公開サブパッケージを列挙（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）し、カレントワーキングディレクトリに依存しない .env 自動読み込みを提供。
  - .env/.env.local の読み込み順・上書き挙動（OS 環境変数保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パース器を実装（export 前置、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定等に対応）。
  - 必須環境変数取得ヘルパー _require と、J-Quants / kabu / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルのプロパティを備えた Settings クラスを公開（settings）。
  - env / log_level の値検証と便利フラグ is_live / is_paper / is_dev を実装。
- AI モジュール（src/kabusys/ai）。
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - target_date に対するニュース収集ウィンドウ計算（JST→UTC 変換）の calc_news_window を実装。
    - raw_news と news_symbols を集約して銘柄毎のテキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄毎センチメントスコアを取得する score_news を実装。
    - バッチ処理（1 API 呼び出し当たり最大 20 銘柄）、1 銘柄あたりの記事数制限・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフ、レスポンスの堅牢なバリデーション、スコアの ±1.0 クリップを実装。
    - DuckDB への書き込みは部分失敗を考慮し、既存スコアを不要に消さないようコード絞り込みで DELETE → INSERT を行う（冪等性確保）。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（ma200_ratio）を計算し（ルックアヘッド防止のため target_date 未満データのみ使用）、マクロ経済ニュースの LLMセンチメントと重み合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - OpenAI 呼び出しのリトライ/バックオフ、API 失敗時のフォールバック（macro_sentiment=0.0）、および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 設計上、内部で datetime.today() を参照せず、ルックアヘッドバイアスを避ける設計。
- データプラットフォーム（src/kabusys/data）。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックという一貫した挙動を実装。最大探索日数制限や健全性チェックを導入。
    - JPX カレンダー夜間バッチ更新処理 calendar_update_job を実装し、J-Quants クライアント経由で差分取得→冪等保存（バックフィル・サニティチェック含む）を行う。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL の実行結果／品質問題／エラー情報を構造化して返却・ロギングできる仕組みを提供。etl モジュールで ETLResult を再エクスポート。
    - 差分取得のためのユーティリティ（テーブル存在確認 / 最大日付取得）を実装。
- リサーチモジュール（src/kabusys/research）。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M）、200 日 MA 乖離（ma200_dev）、Volatility（20 日 ATR）・流動性指標（20 日平均売買代金・出来高比率）、Value（PER/ROE）等の計算関数を実装。DuckDB 上の SQL とウィンドウ関数で実現。
    - データ不足時は None を返す等、安全に扱える仕様。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証）、ランク相関を使った IC 計算 calc_ic（Spearman ランク相関実装）、ランク化ユーティリティ rank、統計サマリー factor_summary を提供。
    - 外部依存を使わず標準ライブラリのみで実装。
- DB/実装上の堅牢化
  - DuckDB の executemany に対する空リスト回避や、ROLLBACK が失敗した場合の警告ログ、NULL 値取り扱い時のログ出力等、実運用を想定したフェイルセーフを多数実装。
- ドキュメント的コメント
  - 各モジュールに処理フロー・設計方針・注意点（ルックアヘッドバイアス回避等）を詳細に記載。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（実装レベルでのフェイルセーフ／例外処理を多数追加）。

Security
- OpenAI API キーは明示的に引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する形で利用。未設定時は ValueError を返すことで意図しない API 呼び出しを防止。

Notes / Implementation details
- ルックアヘッドバイアス防止のため、スコア生成関数（score_news, score_regime, calc_* など）は内部で datetime.today()/date.today() に依存せず、必ず target_date を明示的に受け取る設計です（一部バッチジョブ calendar_update_job は date.today() を利用）。
- OpenAI 呼び出しは json-mode を期待するが、実運用での不整合（前後余計なテキスト混入等）にも対処する復元ロジックを実装しています。
- DuckDB への書き込みは部分失敗時に既存データを不用意に消さないよう、書き込みコードを工夫しています（書き換え対象コードを限定した DELETE → INSERT の実装など）。
- テスト容易性のため、外部 API 呼び出し箇所は patch による差し替えがしやすい構成になっています（内部の _call_openai_api 等）。

今後の改善案（メモ）
- 単体テスト用のモッククライアントや CI 用の小さな DuckDB fixture の追加。
- レスポンス検証ルールの強化（スキーマ検証ライブラリ導入等）。
- スケーリング（並列バッチ、非同期呼び出し選択）の検討。

---
この CHANGELOG は、リポジトリ内のソースコードから機能・設計意図を推測して作成しています。実際の開発履歴やコミットログと差異がある可能性があります。