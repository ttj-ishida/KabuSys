CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠します。

[詳細](https://keepachangelog.com/ja/1.0.0/)

未リリース
---------

（現在なし）

[0.1.0] - 2026-03-31
-------------------

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にてバージョン (0.1.0) と公開モジュールを定義。
- 設定/環境変数管理 (kabusys.config)
  - .env および .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込みの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの実装:
    - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォート有無による差異）。
    - override と protected（OS 環境変数を保護）オプション。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値など主要設定プロパティを提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
    - is_live / is_paper / is_dev といったユーティリティプロパティ。
- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄別にまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - 処理単位と安全策:
      - タイムウィンドウ計算（JST ベース→DB 比較は UTC naive datetime を使用）、前日 15:00 JST ～ 当日 08:30 JST を扱う calc_news_window 実装。
      - 1 チャンク最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
      - JSON Mode 応答のバリデーションと復元処理（余計な前後テキストの復元ロジック）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
      - スコア ±1.0 にクリップ、部分成功時は対象コードのみ置換（DELETE → INSERT）して既存スコアを保護。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からデータ取得、ma200 ratio 計算、マクロキーワードでフィルタした記事を LLM へ送信。
    - LLM 呼び出しはリトライ/バックオフを実装、失敗時は macro_sentiment=0.0（中立）でフェイルセーフ。
    - レジームはスコアをクリップし閾値でラベル化、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性: news_nlp とは独立した _call_openai_api 実装（モジュール結合低減）。
- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー取得/更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存。
    - 営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索範囲上限を設定して無限ループ防止。
    - バックフィル／健全性チェック（最終日が過度に未来の場合はスキップ）を実装。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開して ETL 実行結果の構造化（取得数・保存数・品質問題・エラー）を提供。
    - 差分更新・バックフィル・品質チェック方針を実装に反映する基礎を追加（jquants_client / quality との連携を想定）。
    - データベース存在チェックや最大日付取得ユーティリティなどの内部関数を実装。
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート。
- 研究モジュール (kabusys.research)
  - factor_research:
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev を計算する calc_momentum を実装。
    - ボラティリティ/流動性: atr_20 / atr_pct / avg_turnover / volume_ratio を計算する calc_volatility を実装。
    - バリュー: per / roe を計算する calc_value を実装（raw_financials の最新報告を結合）。
    - DuckDB を用いた SQL ベースの高性能集計。
  - feature_exploration:
    - 将来リターン計算: calc_forward_returns（任意の horizon をサポート）。
    - IC（Information Coefficient）計算: calc_ic（Spearman のランク相関を実装）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
  - 研究用ユーティリティは外部ライブラリ非依存（標準ライブラリ＋DuckDB）。
- ロギング/設計上の安全策
  - ほとんどの長時間処理箇所でログ出力を追加（INFO/WARNING/DEBUG）。
  - AI モジュールおよび ETL/カレンダーで失敗時フェイルセーフ（例外非破壊・部分保存）を採用。
  - ルックアヘッドバイアス防止: 各スコア算出関数は内部で datetime.today()/date.today() を直接参照せず、必ず target_date を受け取る設計。

Changed
- 新規プロジェクトのため該当なし。

Fixed
- 新規プロジェクトのため該当なし。

Known Issues / Notes
- pipeline._get_max_date の末尾付近に実装崩れ（コード断片 "return date.fro"）が確認されます。これはトランスクリプトの切れまたはタイプミスであり、そのままでは構文エラー／実行時エラーになります。リポジトリ本体での修正が必要です（正しくは date.fromisoformat 等をハンドルする実装の完成を想定）。
- OpenAI SDK の使用箇所は client.chat.completions.create を直接呼んでいます。実行環境の OpenAI SDK のバージョンによっては API 呼び出しインターフェースが異なる可能性があるため、デプロイ前に SDK 互換性確認を推奨します。
- news_nlp/regime_detector の LLM 呼び出しは JSON Mode を想定した厳密な JSON 出力を期待していますが、現実の応答で逸脱が発生する場合の復元ロジックを実装しています（ただし完全ではないケースがあり得ます）。
- DuckDB のバインド制約（executemany に空リストを渡せない等）に対して考慮を入れていますが、使用する DuckDB のバージョンにより挙動差が発生する可能性があります。運用環境の DuckDB バージョンでの動作確認を推奨します。

Breaking Changes
- なし（初回リリース）

Security
- なし（初回リリース）

----- End of CHANGELOG -----