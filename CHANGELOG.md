# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初回リリースを含む主要な機能実装の要約を示します。

## [0.1.0] - 2026-04-03

### 追加（Added）
- パッケージ初期リリース: kabusys - 日本株自動売買・データプラットフォーム基盤
  - パッケージ公開情報:
    - バージョン: 0.1.0
    - エントリポイント: src/kabusys/__init__.py（__all__ に data, strategy, execution, monitoring を公開）

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - OS 環境変数を保護するための protected キーセットを導入し、.env.local を override（上書き）できる挙動を実装。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応。
  - .env 行パーサの実装（コメント行、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート）。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - J-Quants / kabu ステーション / LINE Messaging / データベースパス（duckdb/sqlite）/ 監視用ファイルパス/閾値（CPU/Memory/Disk）など。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI: ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を基に、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（ai_score）を計算。
  - 処理要点:
    - スコアリング対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 換算で前日 06:00 ～ 23:30）。
    - 1銘柄あたり最大記事数 / 最大文字数でトリム（トークン肥大化対策）。
    - 1回の API コールで最大 20 銘柄を処理するチャンク処理。
    - 429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフによるリトライ実装。
    - レスポンスの厳格なバリデーション（JSON パース、results リスト、code と score の存在・型チェック、未知コードの無視、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは部分失敗に耐えるように、スコアを取得した code のみ DELETE → INSERT（冪等的置換）を行う実装（DuckDB 0.10 の executemany 空リスト制約に配慮）。
  - テスト容易性: _call_openai_api をパッチ差し替え可能（unittest.mock.patch 用意）。

- AI: 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で書き込み。
  - 処理要点:
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事はタイトルベースでキーワードフィルタ（定義済みのマクロキーワード群）。
    - OpenAI 呼び出しは gpt-4o-mini を利用。失敗時は macro_sentiment=0.0 としてフォールバック。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値により "bull"/"neutral"/"bear" を判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等書き込み、失敗時には ROLLBACK を試行。

- 研究（Research）モジュール（src/kabusys/research/）
  - factor_research.py: モメンタム / ボラティリティ / バリュー 等の定量ファクター計算関数を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev（200 日 MA 乖離）を DuckDB SQL で算出。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比などを算出。
    - calc_value: raw_financials から最新の EPS/ROE を取得し PER/ROE を算出（EPS=0 等のケースは None を返す）。
  - feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、ランク変換、ファクター統計サマリー（count/mean/std/min/max/median）等を実装。
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）を一度のクエリで取得。
    - calc_ic: factor_records と forward_records を code で結合してスピアマンランク相関を計算（有効レコード < 3 は None）。
    - rank / factor_summary 実装（外部ライブラリに依存せず、標準ライブラリのみで実装）。

- データ（Data）モジュール（src/kabusys/data/）
  - calendar_management.py:
    - market_calendar をベースに営業日判定/is_sq_day/next_trading_day/prev_trading_day/get_trading_days の API を提供。
    - market_calendar が未取得な場合は曜日ベース（週末除外）でフォールバック。
    - カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants 経由で差分取得、バックフィル、健全性チェック、冪等保存）。
  - pipeline.py / etl.py:
    - ETLResult データクラスを定義（ETL の取得数・保存数・品質チェック結果・エラー等を格納）。
    - ETL の差分更新、バックフィル戦略、品質チェック連携（quality モジュール）を想定した設計。
    - jquants_client を利用した差分取得・保存ロジックと、呼び出し元が挙動を判断できるエラー/品質情報の収集方針。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### セキュリティ（Security）
- 初回リリースのため該当なし。

### 設計上の重要ポイント（ドキュメント的補足）
- ルックアヘッドバイアス防止:
  - AI スコアリング / レジーム判定 / ファクター計算等、全ての処理で datetime.today() / date.today() を参照しない設計。外部から明示的に target_date を渡して処理を決定することで将来情報の漏洩を防止。
- フェイルセーフ:
  - OpenAI API の失敗時は基本的に例外を上位に投げず、スコアに中立値（0.0）を使う・当該チャンクをスキップする等の耐障害設計になっている。
- 冪等性:
  - DB への書き込みは可能な限り冪等性を保つ（DELETE → INSERT や ON CONFLICT 相当の保存を想定）。
- DuckDB 互換性配慮:
  - executemany に空リストを与えられない（DuckDB 0.10 の制約）ため、空チェックを実装。
- テスト容易性:
  - OpenAI 呼び出し箇所（_call_openai_api）を patch 可能にしてユニットテストでモックできるようにしている。
- 外部依存の最小化:
  - 研究系の統計処理は pandas 等を使わず標準ライブラリと DuckDB SQL のみで実装。

---

今後のリリースでは、以下のような項目を想定しています:
- strategy / execution / monitoring モジュールの具体的な取引ロジック・オーダー発行実装
- テストカバレッジの増強と CI 設定
- パフォーマンス最適化（大規模データ対応のクエリ改善や並列処理）
- ドキュメント追加（API 使用例・運用手順・設定例）

変更点に関する補足や、リリースノートでより詳述したい箇所があればお知らせください。