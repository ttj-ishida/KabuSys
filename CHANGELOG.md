# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-03

初期リリース — 日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基礎
  - src/kabusys/__init__.py によりパッケージ定義とバージョン (0.1.0) を追加。
  - パブリックモジュールとして data, strategy, execution, monitoring を公開するスケルトンを用意。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env/.env.local の自動読み込み機能を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 複雑な .env 行のパース対応（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い）。
  - 必須キー検出用の _require()、環境変数検証（KABUSYS_ENV, LOG_LEVEL）を追加。
  - DB/監視関連のパスや閾値などの設定プロパティを提供（DuckDB/SQLiteパス、PID/KILLフラグ、CPU/MEM/DISK 閾値 等）。

- 自然言語処理 / AI
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - 指定時間ウィンドウ（JST ベース）に基づく raw_news の集約と銘柄別テキスト結合を実装。
    - OpenAI（gpt-4o-mini）へバッチ送信し JSON モードで結果を受け取り、ai_scores テーブルへ冪等的に書き込む処理を追加。
    - バッチサイズ、記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証ロジック（JSON 抽出、results フォーマット検証、コード整合性、数値検査、スコアクリップ）を実装。
    - テスト容易化のため OpenAI 呼び出しを差し替え可能に設計（_call_openai_api の patch を想定）。
    - 公開関数: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
    - prices_daily/raw_news からのデータ取得ロジック、OpenAI 呼び出し（gpt-4o-mini）、スコア合成、market_regime テーブルへの冪等書込を実装。
    - API エラーやパース失敗時はフェイルセーフで macro_sentiment=0.0 を採用し処理継続。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- データ基盤 (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定・次/前営業日取得・期間内営業日列挙ロジックを追加。
    - DB データがない/未登録の場合は曜日ベースのフォールバック（週末除外）を使用。
    - カレンダー更新バッチ calendar_update_job(conn, lookahead_days=...) を実装（J-Quants クライアント経由で差分取得・保存、バックフィル、健全性チェック）。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスによる ETL 実行結果の集約と to_dict() を追加。
    - 差分取得、バックフィル、品質チェック統合を行う設計（jquants_client と quality モジュールとの連携を想定）。
    - etl の公開型 ETLResult を再エクスポート (src/kabusys/data/etl.py)。
  - ユーティリティ: テーブル存在チェック、日付最大値取得等の内部ユーティリティを実装。

- 研究用 / 分析 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum, Volatility, Value, Liquidity 等のファクター計算関数を実装:
      - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m, ma200_dev（200 日 MA の乖離）。
      - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
      - calc_value(conn, target_date): PER（EPS が有効な場合）、ROE（最新財務データの取得）。
    - DuckDB 内 SQL とウィンドウ関数を用いた実装。データ不足時は None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None)（複数ホライズンを一度に取得）。
    - スピアマンの IC 計算 calc_ic(factor_records, forward_records, factor_col, return_col)。
    - ランク化ユーティリティ rank(values)（同順位は平均ランク）。
    - 統計サマリー factor_summary(records, columns)：count/mean/std/min/max/median を標準ライブラリのみで計算。
  - 研究用ユーティリティは kabusys.data.stats の zscore_normalize との連携を想定し __all__ を公開。

### 仕様上の設計判断 (Notable design decisions)
- ルックアヘッドバイアス回避
  - 各モジュール（AI/ニュース/ファクター等）は内部で datetime.today()/date.today() を直接参照せず、target_date を必須引数として受け取る設計。
  - DB クエリでは target_date 未満 / 排他条件を用いるなど、未来データの混入を防止。

- 冪等性と部分失敗耐性
  - DB への書き込みは基本的に冪等操作（DELETE→INSERT や ON CONFLICT 方式）で安全に再実行可能。
  - 部分失敗が起きても既存データを不必要に消さないようにコードを限定して書き換える実装。

- API 呼び出しの堅牢化
  - OpenAI 呼び出しは JSON Mode を用い、429/ネットワーク/タイムアウト/5xx を対象に指数バックオフリトライを行う。
  - レスポンスパース失敗時は警告ログを出してスコアをフォールバック（0 やスキップ）し、例外を上位へ投げない方針。

- テスト容易性
  - OpenAI 呼び出しはモジュール内で抽象化されており、unittest.mock.patch により差し替え可能。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 既知の制限 / 注意点 (Known limitations)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY が必須。未設定時は ValueError を送出。
- DuckDB 0.10 系での executemany 空リストバインドの制約に対する対応が含まれる（空 params の場合は executemany を呼ばない）。
- news_nlp/regime_detector は gpt-4o-mini を前提としており、モデルの仕様変更により応答パースが破壊される可能性がある。
- 一部モジュール（strategy, execution, monitoring）はパッケージ公開されているが、今回の差分では実装スニペットや完全な実装が含まれていない場合がある（スケルトン/設計が中心）。

---

今後の予定:
- strategy / execution / monitoring の具体的な売買ロジック・発注処理の実装・テストを追加予定。
- 品質チェックモジュールの拡充と ETL ワークフローの自動化強化。
- ドキュメント（API 仕様、運用手順、テストケース）の整備。

もしこの CHANGELOG の表現・粒度を変更したい、または特定モジュールについてより詳細なリリースノートを追加したい場合は指示してください。