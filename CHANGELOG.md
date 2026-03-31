# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
このファイルはコードベース（src/kabusys 配下）の実装内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- バージョンは PEP440 準拠の __version__（src/kabusys/__init__.py）に合わせています。
- 日付はこの CHANGELOG 作成日（2026-03-31）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース:
  - 基本パッケージ構成を追加（kabusys モジュール、サブパッケージ: data, ai, research, など）。
  - バージョン識別: __version__ = "0.1.0"。

- 環境設定管理:
  - .env / .env.local 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。  
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
    - .env パーサーは export プレフィックス、クォート／エスケープ、行内コメントに対応。
    - 既存 OS 環境変数は protected として上書き保護。
  - Settings クラスを提供し、アプリ固有の環境変数をプロパティ経由で取得（J-Quants / kabu / Slack / DB パス / 環境種類 / ログレベルなど）。入力検証（列挙値チェック、必須キー未設定時の例外）を実装。

- AI 関連機能:
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）:
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込み。
    - タイムウィンドウは JST ベースで計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換して扱う）。
    - バッチ処理、1チャンク最大 20 銘柄、1銘柄あたり記事・文字数上限でトリム。
    - JSON Mode を想定した厳格なレスポンス検証と復元ロジック（余分な前後テキストが混ざるケースへの対処）。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - スコアは ±1.0 にクリップ。部分失敗時でも他銘柄の既存スコアを保護するため、書き込みは該当コードのみ DELETE → INSERT（冪等）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（内部 _call_openai_api は patch でモック可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルに書き込み。
    - マクロニュースは news_nlp のウィンドウ計算を利用して抽出、OpenAI で評価。
    - API 失敗時に macro_sentiment=0.0 でフォールバックするフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- データプラットフォーム関連:
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）:
    - market_calendar を基に営業日判定・次・前営業日算出・期間内営業日一覧取得・SQ 判定などのユーティリティを実装。
    - market_calendar が未取得または一部欠損している場合の曜日ベースフォールバックを提供（DB 登録値優先）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェック対応）。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）:
    - ETLResult データクラスを実装し ETL 実行結果を structured に管理（品質チェックやエラー情報を含む）。
    - 差分更新・バックフィル・品質チェックの設計を反映（J-Quants クライアント経由の保存や品質問題収集）。
    - data.etl モジュールで ETLResult を公開エクスポート。

- リサーチ（因子研究）機能:
  - factor_research モジュール（src/kabusys/research/factor_research.py）:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等の計算関数を実装。
    - DuckDB 上の SQL とウィンドウ関数を用いて高速に算出。データ不足時の None 処理あり。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、rank ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

- 小さなユーティリティ / 互換性対策:
  - DuckDB の挙動差異（executemany の空リスト不可、list バインドの不安定性など）に対する回避実装。
  - 日付/時刻の取り扱いは timezone 混入を避けるため date/naive datetime で統一。
  - ロギングと警告メッセージを各所に整備しトラブルシュートを容易化。

### 変更 (Changed)
- 該当なし（初回リリースのため既存変更はなし）。

### 修正 (Fixed)
- 該当なし（初回リリースのためバグ修正履歴はなし。ただし設計上のフェイルセーフ・検証ロジックを多用しているため、実運用での問題発見時に個別修正が想定されます）。

### 削除 (Removed)
- 該当なし。

### 廃止予定 (Deprecated)
- 該当なし。

### セキュリティ (Security)
- OpenAI API キー取得は引数注入または環境変数 OPENAI_API_KEY を参照する設計。キー管理は利用者側での適切な取り扱いが必要。

---

注記:
- コード内コメントや docstring に設計方針（ルックアヘッドバイアス回避、冪等性、フェイルセーフなど）が明記されているため、運用時はこれらの前提（DB スキーマ、raw_news / prices_daily 等の存在、OpenAI/J-Quants API の利用許可）を満たしていることを確認してください。
- この CHANGELOG はコード内容からの推測に基づく初期リリース記録です。実際のリリースプロセスで追加の変更点・バージョン番号・日付がある場合は適宜更新してください。