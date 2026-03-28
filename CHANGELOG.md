CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティックバージョニングに従います。

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリースを公開。
- パッケージ構成
  - パッケージ名: kabusys、__version__ = 0.1.0。
  - 公開モジュールの骨組みを配置（data, research, ai 等のサブパッケージを含む）。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト等で使用）。
  - .env の細かいパース実装:
    - export KEY=val 形式対応、クォート文字列内のバックスラッシュエスケープ処理、インラインコメント処理の取り扱い。
  - 環境変数必須チェック用の _require() を提供し、未設定時は明確な ValueError を発生させる。
  - アプリ設定を集約する Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / システムモード等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）。
  - OS 環境変数を保護するための上書きポリシー（.env.local は override、ただし既存 OS 環境は保護）。
- AI 関連 (kabusys.ai)
  - news_nlp モジュール: ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でスコアリングし、ai_scores へ書き込む処理を実装。
    - チャンク単位（最大20銘柄）でのバッチ送信、最大記事数・文字トリム、JSON Mode のレスポンス検証、スコア ±1.0 クリップ。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンスの頑健なパースとバリデーション（余分な前後テキストから JSON を抽出する補正含む）。
    - テスト支援: OpenAI 呼び出し部分をモック可能に設計（内部 _call_openai_api を patch 可）。
    - ニュース収集ウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（内部は UTC naive で扱う calc_news_window を提供）。
  - regime_detector モジュール: ETF（1321）200日移動平均乖離（70%）とマクロセンチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）を実装。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のみを利用、データ不足時は中立 1.0 を使用）。
    - マクロニュース抽出（キーワードフィルタ）→ LLM 評価（gpt-4o-mini）→ 合成・クリップ→ market_regime テーブルへ冪等書き込み。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - テスト支援: news_nlp と独立した _call_openai_api 実装でモジュール結合を避ける。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル操作）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存、バックフィル・健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却。
    - テーブル存在チェック、最大日付取得等のユーティリティ関数を追加。
    - ETL の設計方針として「営業日ベースの差分更新」「バックフィル」「品質チェックの収集と継続処理」を採用。
  - etl モジュール: pipeline.ETLResult を再エクスポート。
  - jquants_client を前提とした保存/取得処理の連携を意識した設計（実際の jquants_client は別モジュール）。
- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などの計算（データ不足時は None）。
    - calc_value: raw_financials と当日の株価から PER / ROE を計算（EPS 0/欠損時は None）。
    - DuckDB SQL を活用した高性能実装。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算（ホライズンのバリデーションあり）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties 回避の工夫あり）。
    - factor_summary: count/mean/std/min/max/median を返す集計ユーティリティ。
  - research.__init__ で主要関数を再エクスポート。
- 共通ユーティリティ・設計上の注意
  - DuckDB を主要な分析 DB として利用（関数引数に DuckDB 接続を受け取る設計）。
  - どのモジュールも datetime.today()/date.today() を勝手に参照せず、外部から target_date を与えることでルックアヘッドバイアスを排除する方針。
  - DB 書き込みは明示的なトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行し例外を伝播。
  - ロギングを多用し、失敗時はログ出力（warning/info/debug/exception）で状況を可観測化。
  - テスト容易性を考え、外部 API 呼び出し部分（OpenAI 呼び出しなど）は差し替え（patch）を想定して分離実装。

Changed
- 初版のため該当項目なし。

Fixed
- 初版のため該当項目なし。

Security
- .env の自動ロードで OS 環境変数を上書きしない保護ロジックを実装（.env.local は上書き可能だが OS 環境キーは protected）。
- OpenAI API キー未指定時には明確なエラーを返す（誤設定を早期検出）。

Notes / 既知の制約・運用上の注意
- 必須の環境変数が未設定の場合、Settings のプロパティ呼び出しや score_news/score_regime は ValueError を投げます。README/.env.example を参照して設定してください。
- 本コードは DuckDB 上に特定のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が存在することを前提としています。初期スキーマ準備は別途行ってください。
- OpenAI との統合は gpt-4o-mini（JSON mode）を前提とした設計です。API レスポンスの形式が変わるとパースエラーになるため、SDK/API バージョンの互換性に注意してください。
- monitoring / strategy / execution 等のパッケージは __init__ で公開予定だが、本リリースで完全実装されていない部分がある可能性があります（将来的な追加予定）。

Authors
- 初期実装: 開発者チーム（コメント・docstring に機能設計を含む）

---

今後のリリースでは、以下を予定しています（例）
- strategy / execution / monitoring の実装と発注ロジックの追加（安全対策やサンドボックスモード含む）
- CI テスト・ユニットテスト拡充（ETL・AI 呼び出しのモック化テスト等）
- パフォーマンス改善とドキュメント整備（API 使用ガイド・運用手順）

もし CHANGELOG に追記してほしい点（例えば日付の変更、より詳細なリリースノート、追加モジュールの明示など）があれば教えてください。