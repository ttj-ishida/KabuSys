# KabuSys

KabuSys は日本株向けの自動売買システム向けに設計された Python パッケージの雛形です。コアとなるパッケージは非常にシンプルな構造になっており、データ取得、戦略、発注（実行）、モニタリングの各コンポーネントを独立して拡張できるように設計されています。

パッケージバージョン: 0.1.0

---

## 目的（プロジェクト概要）

このリポジトリは、日本株自動売買システム（KabuSys）の最小構成テンプレートです。実際の売買ロジックや API 接続は含まず、以下のような主要コンポーネントの雛形を提供します。

- data: 市場データの取得・前処理
- strategy: 売買戦略の実装
- execution: 注文送信・約定管理
- monitoring: ログ・メトリクス・アラート

開発者は各モジュールを実装して、実運用に適した自動売買システムを構築できます。

---

## 機能一覧（現状）

現状はパッケージの雛形のみで、基本的なモジュール構成を提供します。今後、以下のような機能を実装していくことを想定しています。

- データ取得コネクタ（kabuステーション、証券 API、CSV/DB）
- 戦略インターフェース（シグナル生成、リスク管理）
- 注文実行エンジン（成行・指値、注文管理、リトライ）
- モニタリング（ログ出力、メトリクス、通知）

現在の公開 API:
- パッケージルート: `kabusys`（バージョン情報とサブパッケージ）
  - `kabusys.data`
  - `kabusys.strategy`
  - `kabusys.execution`
  - `kabusys.monitoring`

---

## セットアップ手順

このリポジトリは最小構成の Python パッケージです。以下は推奨される開発環境のセットアップ手順です。プロジェクトに pyproject.toml / requirements.txt が含まれていない場合は、必要なライブラリを適宜追加してください。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（推奨）
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 例（実装に応じて追加してください）:
     ```
     pip install --upgrade pip
     pip install pandas numpy requests websocket-client pyyaml
     ```
   - 開発用:
     ```
     pip install black pytest mypy
     ```

4. 開発インストール（プロジェクトルートに pyproject.toml / setup.py がある場合）
   ```
   pip install -e .
   ```
   ※ 現状リポジトリにインストール用のメタファイルがない場合は、直接ソースを使ってください。

5. 動作確認（インタプリタで確認）
   ```
   python -c "import kabusys; print(kabusys.__version__)"
   ```

---

## 使い方（基本例・拡張ガイド）

このパッケージは雛形のため、まずは各モジュールの実装（拡張）を行ってください。以下は利用イメージと実装のためのガイドです。

1. パッケージ読み込み（バージョン確認）
   ```python
   import kabusys
   print(kabusys.__version__)  # 0.1.0
   ```

2. 各コンポーネントの実装方針（例）

   - data:
     - 役割: 株価・板情報・約定履歴などの取得、前処理、キャッシュ
     - 実装例: `kabusys.data.kabu_api.KabuAPIDataProvider`（kabuステーション REST/WebSocket を利用）

   - strategy:
     - 役割: シグナル生成、ポジション管理、リスク管理
     - 実装例: `kabusys.strategy.base.Strategy` を継承して `on_tick()`, `on_candle()` 等のコールバックを実装

   - execution:
     - 役割: 注文送信、注文状態の追跡、約定処理
     - 実装例: `kabusys.execution.executor.Executor` を実装して `send_order()`, `cancel_order()` を提供

   - monitoring:
     - 役割: ログ、メトリクス、アラート（Slack / Email）
     - 実装例: `kabusys.monitoring.logger`, `kabusys.monitoring.alerts`

3. サンプルの擬似コード（戦略→実行の流れ）
   ```python
   # 擬似コード（実装は各自で）
   from kabusys.data import DataProvider
   from kabusys.strategy import Strategy
   from kabusys.execution import Executor

   data = DataProvider(...)
   executor = Executor(...)
   strategy = Strategy(...)

   for tick in data.stream_ticks(symbol="7203"):
       signal = strategy.on_tick(tick)
       if signal == "BUY":
           executor.send_order(symbol="7203", side="BUY", qty=100)
   ```

4. テストと静的解析
   - pytest を使ってユニットテストを追加してください。
   - mypy/flake8/black などを導入して品質を担保することを推奨します。

---

## ディレクトリ構成

現在のリポジトリ（主要ファイル）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージのエントリポイント（バージョン等）
│     ├─ data/
│     │  └─ __init__.py       # データ取得関連
│     ├─ strategy/
│     │  └─ __init__.py       # 売買戦略関連
│     ├─ execution/
│     │  └─ __init__.py       # 注文実行関連
│     └─ monitoring/
│        └─ __init__.py       # モニタリング関連
```

- src/kabusys/__init__.py
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

各サブパッケージは現状空の雛形ですが、ここに必要なモジュール（プロバイダ、クラス、ユーティリティ）を追加していきます。

---

## 開発ガイド（短く）

- まずは DataProvider / Strategy / Executor / Monitor の抽象インターフェース（ベースクラス）を定義してください。
- 単体テスト（pytest）を早めに書いて、実装の安全性を確保してください。
- 実運用時は、注文の冪等性、ネットワークエラー対処、ロギング、ドライラン機能を必ず実装してください。
- 外部 API（証券会社）を利用する場合は、認証情報の扱いに注意し、環境変数やシークレット管理を用いてください。

---

## 貢献方法

バグ報告、機能改善、ドキュメント修正などの貢献は歓迎します。プルリクエストを送る前に issue を立て、変更内容の概要を記載してください。

---

何か特定の実装（例えば kabuステーション API 接続、サンプル戦略、バックテストフレームワーク統合など）を希望される場合は、実装対象を教えてください。具体的な実装例やテンプレートを提供します。