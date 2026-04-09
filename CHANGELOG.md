CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is formatted for
semantic versioning.

フォーマット: 日本語

Unreleased
----------

- (なし)

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初版リリース。
- 基本パッケージ情報:
  - src/kabusys/__init__.py にパッケージ名とバージョン (0.1.0) を追加。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理（src/kabusys/config.py）:
  - .env / .env.local の自動読み込み機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルート特定ロジックを実装（.git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサを実装（コメント行、export プレフィックス、引用符付き値、エスケープ対応、インラインコメント処理等）。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供。J-Quants / kabu / LINE / DB / 監視 / システム設定をプロパティ経由で取得。
  - PAPER_FILL_MODE 等の列挙値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証を実装。
  - Path 型での DB パス取得や kill-flag 等運用向け設定を実装。

- AI ニュース/レジーム評価（src/kabusys/ai/*.py）:
  - news_nlp モジュール:
    - raw_news と news_symbols を基に銘柄別ニュース集約を行い、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 銘柄あたりのトークン肥大対策（記事数制限 / 文字数トリム）。
    - バッチサイズ制御（最大 20 銘柄/コール）、リトライ（429/ネットワーク/タイムアウト/5xx を指数バックオフで処理）。
    - レスポンスの厳密なバリデーション（JSON パース復元処理、results リスト/code/score チェック、スコアクリップ）。
    - DuckDB に対する部分置換（DELETE → INSERT）で冪等性と部分失敗時の保護を実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。

  - regime_detector モジュール:
    - ETF 1321（Nikkei 225 連動型 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存。
    - ma200_ratio の計算（target_date 未満のデータのみ使用、データ不足時は中立: 1.0）。
    - マクロニュースは raw_news からマクロキーワードで抽出（最大 20 件）。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数共有しない設計）。
    - API エラーやレスポンスパース失敗時は macro_sentiment を 0.0 にフォールバックし継続（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションロールバック処理。
    - リトライ（最大 3 回、指数バックオフ）や 5xx 判定ロジックを実装。

- データ基盤（src/kabusys/data/*）:
  - calendar_management モジュール:
    - market_calendar を元に営業日判定・前後営業日探索・期間内営業日取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（平日を営業日）でのフォールバックを提供。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による安全ガード、バックフィル・先読み・健全性チェックの実装。
    - calendar_update_job による J-Quants からの差分取得と冪等保存処理（fetch/save フロー、エラー処理）。

  - pipeline / ETL（src/kabusys/data/pipeline.py, etl.py）:
    - ETLResult データクラスを公開（ETL 実行結果の統計・品質問題・エラー一覧を保持）。
    - 差分更新・バックフィル方針、品質チェックの取り扱い方針を実装。
    - jquants_client と quality モジュールを組み合わせる ETL パイプラインの下地を用意。

  - data パッケージの再エクスポート: ETLResult を kabusys.data.etl 経由で公開。

- リサーチ（src/kabusys/research/*）:
  - factor_research:
    - Momentum / Volatility / Value / Liquidity 等の定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した実装。欠損やデータ不足時の None ハンドリング。
    - 200 日 MA、ATR 20 日、出来高/売買代金平均、各種ホライズン（1/3/6 ヶ月相当）を実装。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証、1 クエリ実行設計）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、NaN/不足データ対応）。
    - rank ユーティリティ（同順位は平均ランク、丸め処理で ties 判定の安定化）。
    - factor_summary：count/mean/std/min/max/median を算出する統計サマリー機能。
  - research パッケージ __all__ で主要ユーティリティを再エクスポート。

Changed
- 設計方針の明確化（各モジュールで共通）
  - 全ての AI / ETL / リサーチ処理でルックアヘッドバイアスを防止するために date.today()/datetime.today() を直接参照しない設計を採用。
  - OpenAI 呼び出しについてはリトライやバックオフ、エラーハンドリング方針を統一。
  - DuckDB のバージョン依存（executemany に空リスト不可など）に対応する実装上の注意を反映。

Fixed
- API 呼び出しや DB 書き込み失敗時のフェイルセーフ挙動を明確化・実装（LLM の失敗はスコアに 0 を使う等）。
- DuckDB におけるトランザクション処理での ROLLBACK 失敗時に警告を出すよう改善。

Security
- 環境変数ロード時に OS 環境変数を保護する protected ロジックを導入（.env の上書き制御）。
- API キー未設定時は明示的に ValueError を送出し誤操作を防止。

Notes / Implementation details
- OpenAI の JSON Mode を利用し厳密 JSON レスポンスを期待するが、実装は余計な前後テキスト混入に耐える復元処理を行う。
- news_nlp と regime_detector は内部でそれぞれ独立した _call_openai_api を持ち、モジュール結合を避ける設計。
- 各所でのトランザクションは明示的に BEGIN / COMMIT / ROLLBACK を使用し、部分成功時に既存データを保護するために削除対象を限定する実装。

未解決 / 今後の課題
- strategy / execution / monitoring の実装は本リリースでの公開 API には含まれますが、詳細実装は今後のバージョンで拡張予定。
- jquants_client / quality モジュールの外部依存箇所はテスト・モックを整備してさらに堅牢化する予定。

--- 

リリース日: 2026-04-09

（この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートとして利用する際は、プロジェクトの正式なリリース情報と照合してください。）