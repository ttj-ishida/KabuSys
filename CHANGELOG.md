Keep a Changelog
=================

すべての重要な変更をこのファイルで記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

フォーマットは Keep a Changelog に準拠しています（https://keepachangelog.com/ja/）。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース:
  - src/kabusys/__init__.py
    - パッケージメタ情報と公開サブパッケージの定義（data, strategy, execution, monitoring）。
  - 環境設定管理:
    - src/kabusys/config.py
      - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ロード実装。
      - .env の行パーサ（コメント、export プレフィックス、クォート内エスケープ、インラインコメント処理対応）。
      - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）、プロジェクトルート探索（.git / pyproject.toml）。
      - Settings クラス（J-Quants, kabuステーション, Slack, DB パス, 監視閾値, 環境・ログレベル検証など）。
      - 必須環境変数未設定時に ValueError を投げる require ロジック。
- AI（自然言語処理）:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信しセンチメントを算出。
    - 時刻ウィンドウの計算（JST ベース → DB 比較は UTC naive datetime）。
    - バッチ処理、1銘柄あたりの文字数制限、最大記事数制限、レスポンスバリデーション（results 配列、code の正規化、数値チェック）実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ。
    - DuckDB への冪等書き込み（DELETE→INSERT、部分失敗時に他コードの既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出しの差し替えポイントを用意（内部関数を patch 可能）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）と JSON パース、リトライ/バックオフ、API 失敗時のデフォルトフォールバック（macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止設計（date.today() を参照せず、prices_daily は target_date 未満データのみ使用）。
- データプラットフォーム / ETL:
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラス（ETL の各種集計、品質問題リスト、エラーリスト、has_errors / has_quality_errors 判定、辞書変換）。
    - 差分更新・バックフィル、品質チェック方針（Fail-Fast ではなく検出を集約して上位が判断する）。
    - DuckDB テーブル存在チェックや最大日付取得などのユーティリティ（ETL 用）。
- カレンダー管理:
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）とカレンダー関連ユーティリティ群。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の実装。
    - market_calendar が未整備な場合の曜日ベースのフォールバック、データ不整合時の健全性チェック、バックフィルの実装。
    - J-Quants クライアント呼び出しラッパー経由の差分取得 → 保存ロジック。
- リサーチ / ファクター:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 戻し方針、スキャン範囲バッファ設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（Spearman の ρ）、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）。
    - pandas 等外部ライブラリに依存しない純 Python 実装。
  - src/kabusys/research/__init__.py による公開 API 集約。
- データユーティリティ:
  - src/kabusys/data/__init__.py（モジュール構成のための基礎ファイル）
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

Security / Validation
- OpenAI API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を利用可能。未設定時は明示的に ValueError を発生させることで誤実行を防止。
- 環境変数読み込み時に OS 環境変数を保護する protected 機能を実装（.env.local は override=True による上書きが可能だが OS 環境優先）。

Design / Implementation Notes
- ルックアヘッドバイアス対策:
  - ニュース・レジーム・ETL・リサーチ系の処理はいずれも内部で date.today()/datetime.today() を直接参照せず、target_date を明示的に受け取る設計。
- DuckDB 互換性:
  - executemany に空リストを渡せないケースを考慮した guard（空時は呼ばない）。
  - テーブル存在チェック・日付変換ユーティリティを提供。
- 冪等性:
  - market_regime / ai_scores / データ保存処理は既存データを削除してから挿入する（部分失敗時に他データを保護する実装や ON CONFLICT を想定した設計）。

Known limitations / Notes
- 一部の処理は外部 API（OpenAI, J-Quants）に依存するため、API サービスの仕様変更やエラー発生に対する耐性はリトライやフェイルセーフであるが、上位での監視や運用ルールが必要。
- 現フェーズでは ai_score と sentiment_score を同一視している（将来の拡張余地あり）。
- raw_financials の PBR・配当利回りなどは未実装（将来の拡張ポイント）。
- calendar_update_job の save / fetch 実装は jquants_client (kabusys.data.jquants_client) に依存（当該クライアントの実装に応じて動作）。

参考 / テストフック
- OpenAI 呼び出しの内部関数（_kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api 等）はテスト用に patch できるように分離されているため、ユニットテストでのモック差替えが可能。

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴・タグ・PR 要約や運用上の注意点を追記してください。