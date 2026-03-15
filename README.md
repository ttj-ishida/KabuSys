# KabuSys

KabuSys は日本株の自動売買システムの骨組み（スケルトン）です。データ取得、トレード戦略、注文実行、監視・ログの各コンポーネントを分離した構成になっており、独自の戦略や実行エンジンを実装して拡張できます。

現在のバージョン: 0.1.0

---

## プロジェクト概要

本リポジトリは自動売買システムを構築するための基本パッケージ構成を提供します。以下のような役割ごとにサブパッケージを分けており、各パッケージ内に機能を実装していく想定です。

- data: 市場データの取得・前処理
- strategy: 売買ルール・シグナル生成
- execution: 注文発注・約定管理
- monitoring: 実行状況や資産推移の監視・ロギング

このリポジトリは「枠組み（テンプレート）」を提供することを目的としており、外部 API キーや取引所固有の実装は含みません。自分の環境や利用する API に応じて実装・設定してください。

---

## 機能一覧

現在の実装はパッケージ構成のみ（スケルトン）です。今後追加・実装すべき代表的な機能は以下のとおりです。

- データ取得
  - 約定・板情報、日次・分足データの取得
  - 履歴データのキャッシュ・前処理
- 戦略（strategy）
  - シグナル生成（テクニカル指標、裁定、機械学習モデルなど）
  - ポジション管理（サイズ、リスク管理）
- 注文実行（execution）
  - 成行・指値注文の発注・キャンセル
  - 注文履歴の追跡・再試行
- 監視・通知（monitoring）
  - 実行ログ、パフォーマンス指標の収集
  - エラー通知（Slack / Email など）

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨

手順の例（ローカル開発用）:

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - requirements.txt を用意している場合:
     ```
     pip install -r requirements.txt
     ```
   - 開発中にパッケージを編集して使いたい場合（プロジェクトルートに setup.py / pyproject.toml がある想定）:
     ```
     pip install -e .
     ```

4. 環境変数 / 設定
   - 外部 API を利用する場合は API キーや接続情報を環境変数や設定ファイルに保存してください。例:
     - KABU_API_KEY
     - KABU_API_SECRET

※ 本リポジトリは雛形のため、実際に動作させるには各サブパッケージ内に実装を追加する必要があります。

---

## 使い方（例）

基本的な使い方の例を示します。現状は各サブパッケージが空のため、まずは簡単な確認としてバージョン確認やパッケージのインポートを行います。

Python REPL またはスクリプト内で:
```python
import kabusys

# バージョン確認
print(kabusys.__version__)

# サブパッケージにアクセス（現状は空のパッケージ）
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

サブパッケージに実装を追加する例（strategy 内にシンプルな戦略クラスを置く場合）:
```python
# src/kabusys/strategy/my_strategy.py

class MyStrategy:
    def __init__(self):
        pass

    def on_tick(self, tick):
        # tick を受け取ってシグナルを返す
        return None
```

実行モジュール（execution）と連携して、シグナルに基づいて注文を出すようなフローを作成してください。

---

## ディレクトリ構成

現状の主要ファイル・ディレクトリ構成は以下の通りです。

- README.md
- src/
  - kabusys/
    - __init__.py           # パッケージ定義、バージョン情報
    - data/
      - __init__.py         # データ取得・前処理用のモジュールを配置
    - strategy/
      - __init__.py         # 戦略実装を配置
    - execution/
      - __init__.py         # 注文発注や接続ロジックを配置
    - monitoring/
      - __init__.py         # ログ・監視関連の実装を配置

例（ツリー表示）:
```
.
└─ src/
   └─ kabusys/
      ├─ __init__.py
      ├─ data/
      │  └─ __init__.py
      ├─ strategy/
      │  └─ __init__.py
      ├─ execution/
      │  └─ __init__.py
      └─ monitoring/
         └─ __init__.py
```

---

## 拡張ガイド（簡単な提案）

- data/: 外部 API クライアント（例: kabu API クライアント）や CSV 読み込み、キャッシュ層を実装
- strategy/: 戦略ごとにクラスを分け、共通インターフェイス（on_tick, on_bar, initialize, finalize など）を定義
- execution/: 実際の注文発注処理、テスト用のモック実装、リトライやレートリミット対策を実装
- monitoring/: ロギング、メトリクス収集、アラート（Slack, Email など）のためのラッパーを用意

ユニットテストや CI の導入、設定ファイル（YAML/JSON/TOML）による戦略・接続情報の外部化を行うと運用しやすくなります。

---

この README はプロジェクトの初期テンプレートです。必要に応じて、実装が増えたら「使い方」「設定」「API キーの管理方法」「運用時の注意点」などを追記してください。