# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: 本 CHANGELOG はソースコードの内容から機能・設計意図を推測して作成しています。

## [0.1.0] - 2026-03-28
初回リリース

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン 0.1.0
  - 公開モジュール: data, research, ai, その他のサブパッケージを含むインターフェースを __all__ で定義

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して特定（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - OS 環境変数は protected として上書き保護
  - .env の行パーサ実装
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応
    - 無効行やコメント行を無視
  - Settings クラスを提供
    - J-Quants / kabu API / Slack / データベースパス等のプロパティを環境変数から取得
    - 必須変数未設定時は ValueError を送出
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション
    - パス系は Path 型で返却（expanduser() 対応）
    - is_live / is_paper / is_dev の利便性プロパティ

- データ処理 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルと連動した営業日判定 API を提供
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB の登録データを優先、未登録日は曜日ベースでフォールバック（休日は土日扱い）
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止
    - calendar_update_job による J-Quants からの差分取得・バックフィル機構
      - lookahead / backfill / sanity チェックを実装
      - J-Quants クライアント経由で取得 → 保存（冪等）して結果数を返却
  - ETL・パイプライン (pipeline, etl)
    - ETLResult dataclass を定義（ETL 実行の集約結果、品質問題・エラーを含む）
    - _get_max_date 等のユーティリティと差分更新設計方針を実装
    - ETL の設計において:
      - 差分更新（営業日ベース）、backfill による後出し修正吸収
      - 保存は Idempotent（ON CONFLICT / DELETE→INSERT 等）を想定
      - 品質チェックの収集を行うが、呼び出し元が対処を決定する（Fail-Fast ではない）
    - kabusys.data.etl は ETLResult を公開再エクスポート

- 研究・ファクター計算 (kabusys.research)
  - factor_research モジュール
    - モメンタム (calc_momentum)
      - 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を計算
      - データ不足時は None を返す（安全設計）
    - ボラティリティ / 流動性 (calc_volatility)
      - 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
      - true_range の NULL 伝播管理により ATR の正確なカウントを実装
    - バリュー (calc_value)
      - raw_financials から直近財務データを取得して PER / ROE を計算
      - EPS が 0 または NULL の場合は PER を None に
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（外部 API へ影響しない）
  - feature_exploration モジュール
    - 将来リターン計算 (calc_forward_returns)
      - 複数ホライズン対応（デフォルト [1,5,21]）、horizons のバリデーションを実装
      - 単一クエリで効率的に取得、スキャン期間は最大ホライズンの 2 倍のカレンダーバッファを使用
    - IC 計算 (calc_ic)
      - Spearman ランク相関（ランクは平均ランクで ties を処理）
      - 有効レコードが 3 未満の場合は None を返す
    - ユーティリティ rank、統計サマリー (factor_summary) を提供
      - factor_summary は count/mean/std/min/max/median を計算（None を除外）
    - pandas 等の外部依存を使わず標準ライブラリと DuckDB で実装

- AI / NLP 機能 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）
    - 1 銘柄あたり最大記事数・文字数でトリム（トークン肥大化対策）
    - OpenAI (gpt-4o-mini) を JSON Mode でバッチ送信（最大 _BATCH_SIZE=20 銘柄/コール）
    - 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ
    - レスポンスのバリデーションとスコア ±1.0 にクリップ
    - 書き込みは部分置換（対象コードのみ DELETE → INSERT）して部分失敗時に既存スコアを保護
    - テスト容易性: _call_openai_api をパッチ差し替え可能
  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321 の 200 日 MA 乖離 (重み 70%) と、マクロニュースの LLM センチメント (重み 30%) を合成して日次でレジーム判定
    - マクロニュース抽出は news_nlp.calc_news_window を利用
    - OpenAI (gpt-4o-mini) を使用、JSON レスポンスを期待
    - ルール:
      - 合成スコアを -1..1 にクリップ
      - 閾値により "bull"/"neutral"/"bear" を判定
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - テスト容易性: _call_openai_api をパッチ差し替え可能、api_key は引数または環境変数で注入

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- API キー等の必須設定は Settings で明示的に要求し、未設定時は例外を投げることで誤動作を防止

---

開発上の注意点・設計に関する補足
- ルックアヘッドバイアス対策: 日付判定やウィンドウ計算は内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に与える）。
- DuckDB 互換性への配慮: executemany に空リストを渡さない等の実装上の注意がある（DuckDB 0.10 の制約対応）。
- テスト容易性: OpenAI 呼び出しといくつかの I/O に対して差し替え可能なレイヤを用意。
- フェイルセーフ設計: 外部 API 失敗時は例外破壊的に停止させず、局所的にフォールバックするかスキップし、呼び出し元が対処できるよう ETLResult 等でエラー情報を集約する方針。

（以降のリリースでは、個別機能の拡張・バグ修正・API 互換性の変更等をこのファイルに記載してください。）