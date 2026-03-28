# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- 初回リリース。
- パッケージのメタ情報を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート済みサブパッケージ: data, strategy, execution, monitoring

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（読み込み順: OS 環境 > .env.local > .env）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境変数保護機構（既存 OS 環境変数を保護して .env の上書きを制御）。
  - Settings クラスを公開（settings インスタンス）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得（未設定時は ValueError）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）を検証。
    - デフォルトの DB パス: duckdb → data/kabusys.duckdb, sqlite → data/monitoring.db
    - ユーティリティプロパティ: is_live, is_paper, is_dev

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: ニュース記事を集約して OpenAI（gpt-4o-mini）に JSON Mode で問合せ、銘柄ごとのセンチメント（ai_scores）を計算・保存する。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウで記事収集（UTC へ変換）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数/文字数のトリム、レスポンス検証、スコア ±1.0 にクリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。失敗時はスキップ（フェイルセーフ）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を確保。
  - regime_detector.score_regime: ETF（1321）200日移動平均乖離（重み70%）とニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する。
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロ記事抽出はキーワードベース（定義済みキーワード群）、最大 20 記事。
    - OpenAI 呼び出しは専用ラッパーで行い、API エラーに対するリトライ・フェイルセーフを実装。
    - market_regime テーブルへは冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ユーティリティ（market_calendar を元に営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得時は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して市場カレンダーを更新（バックフィル、健全性チェック、冪等保存）。
  - pipeline
    - ETL パイプラインの結果表現に ETLResult を追加（取得数・保存数・品質問題・エラーメッセージ等を保持）。
    - 差分取得、バックフィル、品質チェックとの連携方針をコードドキュメントで明示。
  - etl モジュールから ETLResult を再エクスポート（kabusys.data.ETLResult）

- 研究用機能（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と株価から PER/ROE を算出（最新財務レコードを target_date 以前から選択）。
    - 各関数は DuckDB SQL を中心に実装し、(date, code) キーの dict リストを返す設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマン（ランク相関）による IC 計算（最低 3 レコード必要）。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ（丸めで ties の扱い安定化）。
    - factor_summary: カラム毎の count/mean/std/min/max/median を計算（None 値除外）。
  - kabusys.research.__init__ で主要関数を再エクスポート

### Changed
- （該当なし）初回リリースのため履歴なし。

### Fixed
- （該当なし）初回リリースのため履歴なし。

### Security
- 環境変数は明示的に必須項目を検査し、未設定時はエラーを投げる設計（機密情報の未設定ミスを検知）。

### Notes / Implementation details
- ルックアヘッドバイアス対策: AI・研究・ETL の各処理はいずれも内部で datetime.today()/date.today() を直接参照せず、target_date 引数に基づく設計。
- OpenAI 呼び出しは JSON Mode を利用し厳密な JSON を期待する。レスポンスパースや不正フォーマットにはフォールバック処理あり。
- DuckDB への書き込みは互換性を考慮し executemany の空リストバインドを回避する実装（DuckDB 0.10 互換性）。
- フェイルセーフ設計: 外部 API エラーやパースエラー時は例外を上位に伝播させずフォールバック（0.0 や空スコア等）で継続する箇所がある。DB 書き込み失敗時はロールバックして例外を伝播。
- 設計文書（モジュール内 docstring）でデータソース制約（参照するテーブル等）や期待動作を明記。

### Known limitations / Future work
- 一部指標（PBR、配当利回り）は未実装（calc_value の注記）。
- news_nlp / regime_detector の OpenAI 呼び出しはモデル名 gpt-4o-mini に依存。将来 SDK/モデル変更時の互換性確認が必要。
- calendar_update_job と ETL の jquants_client 呼び出しは外部 API 実装に依存するため、ネットワークや API 仕様変更の影響を受ける。
- テスト用フック（_call_openai_api の patch）を想定した実装はあるが、包括的なテストカバレッジが今後の課題。

---

以上。今後のリリースではバグ修正、機能追加（Strategy/Execution/Monitoring の具体的実装）、およびテスト・ドキュメント拡充を予定しています。